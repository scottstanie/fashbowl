# Generated by Django 2.2.10 on 2020-04-07 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20200407_1854'),
    ]

    operations = [
        migrations.AddField(
            model_name='word',
            name='text',
            field=models.CharField(default=None, max_length=500),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='player',
            name='team',
            field=models.CharField(blank=True, choices=[('red', 'red'), ('blue', 'blue')], max_length=500, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='word',
            unique_together={('player', 'text')},
        ),
    ]
