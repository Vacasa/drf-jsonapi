from django.db import models


class Trunk(models.Model):
    name = models.CharField(max_length=128)


class Root(models.Model):
    name = models.CharField(max_length=128)
    trunk = models.ForeignKey(Trunk, on_delete=models.CASCADE, related_name="roots")


class Branch(models.Model):
    name = models.CharField(max_length=128)
    trunk = models.ForeignKey(Trunk, on_delete=models.CASCADE, related_name="branches")


class Leaf(models.Model):
    name = models.CharField(max_length=128)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="leaves")
