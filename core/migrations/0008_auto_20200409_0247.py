# Generated by Django 2.2.10 on 2020-04-09 02:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20200409_0223'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='active_guessing',
            new_name='is_live_round',
        ),
        migrations.RemoveField(
            model_name='game',
            name='round_done',
        ),
        migrations.RemoveField(
            model_name='game',
            name='round_start_time',
        ),
        migrations.AddField(
            model_name='game',
            name='round_start_timeint',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
