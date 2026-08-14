from django.db import migrations, models

# Legacy role -> new role remap for the simplified 6-role model.
# SUPERVISOR had unrestricted access like ADMIN, so it maps to ADMIN.
# TECHNICIAN worked the same tab as WORKSHOP_SUPERVISOR, so it merges into it.
# WAREHOUSE has no equivalent tab in the new model; falls back to read-only
# VIEWER so no access is silently over-granted — reassign manually if needed.
LEGACY_ROLE_REMAP = {
    "SUPERVISOR": "ADMIN",
    "TECHNICIAN": "WORKSHOP_SUPERVISOR",
    "WAREHOUSE": "VIEWER",
}


def remap_legacy_roles(apps, schema_editor):
    FMMSUser = apps.get_model("authentication", "FMMSUser")
    for old_role, new_role in LEGACY_ROLE_REMAP.items():
        FMMSUser.objects.filter(role=old_role).update(role=new_role)


def noop_reverse(apps, schema_editor):
    # Legacy role identity is not recoverable once remapped.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0004_add_workshop_supervisor_role"),
    ]

    operations = [
        migrations.RunPython(remap_legacy_roles, noop_reverse),
        migrations.AlterField(
            model_name="fmmsuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("DRIVER", "راننده"),
                    ("TRANSPORT", "مسئول ترابری"),
                    ("DISTRIBUTION", "مسئول توزیع"),
                    ("WORKSHOP_SUPERVISOR", "مسئول تعمیرات"),
                    ("ADMIN", "مدیر کل"),
                    ("VIEWER", "ناظر کل"),
                ],
                db_index=True,
                default="VIEWER",
                help_text="FMMS role — controls API permissions.",
                max_length=20,
            ),
        ),
    ]
