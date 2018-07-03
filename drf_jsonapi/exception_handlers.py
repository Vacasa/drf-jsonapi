from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.exceptions import FieldError, ValidationError as DjangoValidationError

from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from django.http import Http404, HttpResponseNotFound

from .objects import Document, Error
from .serializers import DocumentSerializer, ErrorSerializer
from .response import CONTENT_TYPE


def jsonapi_exception_handler(exc, context):
    return ExceptionHandler.handle(exc, context)


def handleDjangoErrors(request, exception):
    return ExceptionHandler.handle(exception, None)


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

        :param drf_jsonapi.exception_handlers.ExceptionHandler cls: This class instance
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
                status=getattr(response, 'status_code', 500),
                content_type=CONTENT_TYPE
            )

    @classmethod
    def handle_Error(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an Error exception

        :param drf_jsonapi.exception_handlers.ExceptionHandler cls: This class instance
        :param drf_jsonapi.objects.Error exc: An Exception object
        :param drf_jsonapi.objects.Error context: The stack trace associated with the exception
        :return: A 400 error Response
        :rtype: rest_framework.response.Response
        """

        doc = DocumentSerializer(Document())
        doc.instance.errors = [ErrorSerializer(exc).data]
        return Response(
            doc.data,
            status=getattr(exc, 'status_code', 400),
            content_type=CONTENT_TYPE
        )

    @classmethod
    def handle_APIException(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an APIException exception

        :param drf_jsonapi.exception_handlers.ExceptionHandler cls: This class instance
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
                status=getattr(exc, 'status_code', 400),
                content_type=CONTENT_TYPE
            )
        else:
            error = Error(detail=detail, status_code=status_code)
            doc.instance.errors = [ErrorSerializer(error).data]
            return Response(
                doc.data,
                status=status_code,
                content_type=CONTENT_TYPE
            )

    @classmethod
    def handle_ValidationError(cls, exc, context):  # NOSONAR
        """
        Retrieves a 400 error Response from an APIException exception

        :param drf_jsonapi.exception_handlers.ExceptionHandler cls: This class instance
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
            status=getattr(exc, 'status_code', 400),
            content_type=CONTENT_TYPE
        )

    @classmethod
    def handle_Resolver404(cls, exc, context):  # NOSONAR
        """
        Retrieves a 404 error Response from an Resolver404 exception
        This is thrown when there is no match in urls for the path requested
        It MUST return a django.http.HttpResponseNotFound

        :param cls: This class instance
        :param exc: An Exception object
        :param context: The stack trace associated with the exception
        :return: A 404 error Response
        :rtype: django.http.HttpResponseNotFound
        """
        doc = DocumentSerializer(Document())
        error = Error(
            detail="Endpoint '{}' not found".format(exc.args[0]['path']),
            status_code=404
        )
        doc.instance.errors = ErrorSerializer(error).data

        return HttpResponseNotFound(doc, content_type=CONTENT_TYPE)
