from dagster import AssetSelection, Definitions, define_asset_job, load_assets_from_modules, ScheduleDefinition, DefaultScheduleStatus

from . import assets

all_assets = load_assets_from_modules([assets])

# Addition: define a job that will materialize the assets
weather_data_job = define_asset_job("weather_data_job", selection=AssetSelection.all())

weather_data_schedule = ScheduleDefinition(
    job=weather_data_job,
    cron_schedule="0 * * * *",  # every hour
    default_status = DefaultScheduleStatus.RUNNING,
)

defs = Definitions(
    assets=all_assets,
    schedules=[weather_data_schedule]  
)