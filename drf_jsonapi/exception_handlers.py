from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.exceptions import FieldError, ValidationError as DjangoValidationError

from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework.response import Response as BaseResponse

from .objects import Document, Error
from .serializers import DocumentSerializer, ErrorSerializer


def jsonapi_exception_handler(exc, context):
    return ExceptionHandler.handle(exc, context)


class Response(BaseResponse):

    def __init__(self, *args, **kwargs):
        # kwargs['content_type'] = 'application/vnd.api+json'
        super().__init__(*args, **kwargs)


class ExceptionHandler(object):
    """
    Converts various Exception types into JSON-API error reponses.
    This functionality requires an entry to the REST_FRAMEWORK settings
    dictionary in settings.py:
    'EXCEPTION_HANDLER': 'drf_jsonapi.exception_handlers.jsonapi_exception_handler'
    """

    @classmethod
    def handle(cls, exc, context):
        """
        Retrieves a 500 error Response from a standard Exception

        :param jsonapi.exception_handlers.ExceptionHandler cls: This class instance
        :param Exception exc: An Exception object
        :param dict context: The stack trace associated with the exception
        :return: A 500 error Response
        :rtype: rest_framework.response.Response
        """

        # check for specific handlers for the exc class
        handler_function_name = 'handle_{}'.format(exc.__class__.__name__)

        if hasattr(cls, handler_function_name):
                return getattr(cls, handler_function_name)(exc, context)

        for base_class in exc.__class__.__bases__:
            handler_function_name = 'handle_{}'.format(base_class.__name__)
            if hasattr(cls, handler_function_name):
                return getattr(cls, handler_function_name)(exc, context)

        # Call REST framework's default handler
        response = exception_handler(exc, context)

        if response:
            doc = DocumentSerializer(Document())
            error = Error(
                status_code=getattr(response, 'status_code', 500),
                detail=response.data['detail']
            )
            doc.instance.errors = [ErrorSerializer(error).data]
            return Response(
                doc.data,
                status=getattr(response, 'status_code', 500)
            )

    @classmethod
    def handle_Error(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an Error exception

        :param jsonapi.exception_handlers.ExceptionHandler cls: This class instance
        :param jsonapi.objects.Error exc: An Exception object
        :param jsonapi.objects.Error context: The stack trace associated with the exception
        :return: A 400 error Response
        :rtype: rest_framework.response.Response
        """

        doc = DocumentSerializer(Document())
        doc.instance.errors = [ErrorSerializer(exc).data]
        return Response(
            doc.data,
            status=getattr(exc, 'status_code', 400)
        )

    @classmethod
    def handle_APIException(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an APIException exception

        :param jsonapi.exception_handlers.ExceptionHandler cls: This class instance
        :param rest_framework.exceptions.APIException exc: An Exception object
        :param dict context: The stack trace associated with the exception
        :return: A 400 error Response
        :rtype: rest_framework.response.Response
        """

        doc = DocumentSerializer(Document())

        detail = getattr(exc, 'detail', str(exc))
        status_code = getattr(exc, 'status_code', 400)

        if isinstance(detail, dict):
            # this is for cases where a ValidationError is thrown
            # which has a dict as the detail
            errors = Error.parse_validation_errors(detail)
            doc.instance.errors = ErrorSerializer(errors, many=True).data
            return Response(
                doc.data,
                status=getattr(exc, 'status_code', 400)
            )
        else:
            error = Error(detail=detail, status_code=status_code)
            doc.instance.errors = [ErrorSerializer(error).data]
            return Response(
                doc.data,
                status=status_code
            )

    @classmethod
    def handle_ValidationError(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an APIException exception

        :param jsonapi.exception_handlers.ExceptionHandler cls: This class instance
        :param django.core.exceptions.ValidationError exc: An Exception object
        :param django.core.exceptions.ValidationError context: The stack trace associated with the exception
        :return: A 400 error Response
        :rtype: rest_framework.response.Response
        """

        return cls.handle_APIException(exc, context)

    @classmethod
    def handle_InvalidPage(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an InvalidPage exception

        :param cls: This class instance
        :param exc: An Exception object
        :param context: The stack trace associated with the exception
        :return: A 400 error Response
        :rtype: rest_framework.response.Response
        """

        doc = DocumentSerializer(Document())
        error = Error(
            source={'parameter': 'page[number]'},
            detail=str(exc),
            status_code=400
        )
        doc.instance.errors = [ErrorSerializer(error).data]
        return Response(
            doc.data,
            status=getattr(exc, 'status_code', 400)
        )
