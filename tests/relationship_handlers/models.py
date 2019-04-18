from django.db import models


class Node(models.Model):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True
    )
    links_to = models.ManyToManyField("self", related_name="links_from")
