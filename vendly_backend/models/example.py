from __future__ import annotations

from django.db import models


class ExampleItem(models.Model):
    """
    Minimal example model to demonstrate the models/ folder pattern.
    """

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "example_items"

    def __str__(self) -> str:
        return self.name

