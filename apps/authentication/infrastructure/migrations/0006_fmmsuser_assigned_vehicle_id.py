"""Add admin-assignable vehicle link on FMMSUser (cross-domain by ID only)."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0005_fmmsuser_personnel_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="fmmsuser",
            name="assigned_vehicle_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                default=None,
                help_text=(
                    "Vehicle manually assigned by an admin (cross-domain by ID "
                    "only — no FK to the vehicle app)."
                ),
                null=True,
            ),
        ),
    ]
