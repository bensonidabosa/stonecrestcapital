from django.db import models
from portfolios.models import Portfolio


class CopyRelationship(models.Model):
    follower = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='following'
    )
    leader = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='followers'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'leader')

    def __str__(self):
        return f"{self.follower} copies {self.leader}"
