from django.db import models


class TestModelQuerySet(models.QuerySet):
    def get(self, *args, **kwargs):
        if kwargs["pk"] == 666:
            raise TestModel.DoesNotExist()
        return TestModel(name="Test Model", is_active=True, **kwargs)


class TestModelManager(models.Manager):
    def get_queryset(self):
        return TestModelQuerySet(self.model, using=self._db)

    def get(self, pk, **kwargs):
        return self.get_queryset().get(pk=pk, **kwargs)


class TestModel(models.Model):
    name = models.CharField(max_length=128, null=True)
    count = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    related_things = models.ForeignKey("self", on_delete=models.CASCADE)

    # Override manager so we can mock the methods
    objects = TestModelManager()

    class Meta:
        ordering = ["id"]

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        return self

    def delete(self, using=None, keep_parents=False):
        return self
