from datetime import datetime

import pandas as pd

from quartz_solar_forecast.data import get_nwp, make_pv_data
from quartz_solar_forecast.forecasts import forecast_v1, TryolabsSolarPowerPredictor
from quartz_solar_forecast.pydantic_models import PVSite


def predict_ocf(
    site: PVSite, model=None, ts: datetime | str = None, nwp_source: str = "icon"
):
    """
    Run the forecast with the OCF model
    
    :param site: the PV site
    :param model: the model to use for prediction
    :param ts: the timestamp of the site. If None, defaults to the current timestamp rounded down to 15 minutes.
    :param nwp_source: the nwp data source. Either "gfs" or "icon". Defaults to "icon" 
    :return: The PV forecast of the site for time (ts) for 48 hours
    """
    if ts is None:
        ts = pd.Timestamp.now().round("15min")

    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    # make pv and nwp data from nwp_source
    nwp_xr = get_nwp(site=site, ts=ts, nwp_source=nwp_source)
    pv_xr = make_pv_data(site=site, ts=ts)

    # load and run models
    pred_df = forecast_v1(nwp_source, nwp_xr, pv_xr, ts, model=model)

    return pred_df


def predict_tryolabs(
    site: PVSite, ts: datetime | str = None):
    """
    Run the forecast with the tryolabs model
    
    :param site: the PV site
    :param ts: the timestamp of the site. If None, defaults to the current timestamp rounded down to 15 minutes.
    :return: The PV forecast of the site for time (ts) for 48 hours
    """

    # instantiate class to make predictions
    solar_power_predictor = TryolabsSolarPowerPredictor()

    # download the model from google drive and decompress if necessary
    solar_power_predictor.load_model()
    
    # set start and end time, if no time is given use current time
    if ts is None:
        start_date = pd.Timestamp.now().strftime("%Y-%m-%d")
        start_time = pd.Timestamp.now().floor("15min")
    else:
        start_date = pd.Timestamp(ts).strftime("%Y-%m-%d")
        start_time = pd.Timestamp(ts).floor("15min")

    end_time = start_time + pd.Timedelta(hours=48)

    # make predictions
    predictions = solar_power_predictor.predict_power_output(
        latitude=site.latitude,
        longitude=site.longitude,
        start_date=start_date,
        kwp=site.capacity_kwp,
        orientation=site.orientation,
        tilt=site.tilt,
    )

    # postprocessing of the dataframe
    if predictions is not None:
        predictions = predictions[
            (predictions["date"] >= start_time) & (predictions["date"] < end_time)
        ]
        predictions = predictions.reset_index(drop=True)
        predictions.set_index("date", inplace=True)
        print("Predictions finished.")
        return predictions


def run_forecast(
    site: PVSite,
    model: str = "ocf",
    ts: datetime | str = None,
    nwp_source: str = "icon",
) -> pd.DataFrame:
    """
    Predict solar power output for a given site using a specified model.

    :param site: the PV site
    :param model: the model to use for prediction, choose between "ocf" and "tryolabs",
                    by default "ocf" is used
    :param ts: the timestamp of the site. If None, defaults to the current timestamp rounded down to 15 minutes.
    :param nwp_source: the nwp data source. Either "gfs" or "icon". Defaults to "icon" 
                       (only relevant if model=="ocf")
    :return: The PV forecast of the site for time (ts) for 48 hours
    """

    if model == "ocf":
        return predict_ocf(site, None, ts, nwp_source)
              
    if model == "tryolabs":
        return predict_tryolabs(site, ts)
      
    raise ValueError(f"Unsupported model: {model}. Choose between 'tryolabs' and 'ocf'")
