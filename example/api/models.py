from django.db import models


class Publisher(models.Model):
    name = models.CharField(max_length=128)


class Author(models.Model):
    name = models.CharField(max_length=128)


class Book(models.Model):
    title = models.CharField(max_length=128)
    authors = models.ManyToManyField(Author, related_name="books")
    publisher = models.ForeignKey(
        Publisher, related_name="books", on_delete=models.CASCADE
    )
