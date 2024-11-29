import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

api_google_genai = os.getenv("API_GOOGLE_GENAI_WF")


def fetch_data(api_url_base, latitude, longitude):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=48 * 30)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    api_url = f"{api_url_base}?latitude={latitude}&longitude={longitude}&parameters=PRECTOTCORR,EVPTRNS,GWETROOT,GWETTOP,T2M,ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,CLRSKY_SFC_SW_DNI,WS10M,CLRSKY_DAYS,CLRSKY_KT&format=JSON&start={start_str}&end={end_str}&community=AG"

    response = requests.get(api_url)
    if response.status_code != 200:
        raise ValueError(
            f"Failed to fetch data from API. Status code: {response.status_code}"
        )

    data = response.json()
    parameters = data["properties"]["parameter"]

    parameter_dfs = {}
    for parameter, values in parameters.items():
        df = pd.DataFrame(list(values.items()), columns=["date", parameter])
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        parameter_dfs[parameter] = df

    return parameter_dfs


def clean_and_analyze_t2m_data(df):
    invalid_values = {-999, -9999, -999.0, -9999.0}

    df["is_valid"] = ~df["t2m"].isin(invalid_values)

    monthly_data = (
        df.groupby(df["date"].dt.to_period("M"))
        .agg(
            monthly_avg=("t2m", lambda x: x[x.isin(invalid_values) == False].mean()),
            valid_days=("is_valid", "sum"),
            total_days=("is_valid", "count"),
        )
        .reset_index()
    )

    monthly_data = monthly_data[
        monthly_data["valid_days"] >= 0.5 * monthly_data["total_days"]
    ]

    if monthly_data["monthly_avg"].isna().any():
        print("Warning: NaN detected in monthly averages, filling with safe defaults.")
    monthly_data["monthly_avg"] = monthly_data["monthly_avg"].fillna(
        0
    )  # Replace NaN with 0

    monthly_data["trend"] = (
        monthly_data["monthly_avg"].diff().fillna(0)
    )  # Replace NaN trends with 0

    return monthly_data


def calculate_monthly_trends(monthly_data):
    monthly_data["month"] = monthly_data["date"].dt.month
    monthly_data["pct_change"] = monthly_data["monthly_avg"].pct_change()
    avg_trends = monthly_data.groupby("month")["pct_change"].mean().fillna(0).to_dict()
    return avg_trends


def forecast_with_trends(monthly_data, num_months=4):
    avg_trends = calculate_monthly_trends(monthly_data)

    avg_trends = {
        month: (trend if not pd.isna(trend) else 0)
        for month, trend in avg_trends.items()
    }

    last_avg = monthly_data["monthly_avg"].iloc[-1]
    if pd.isna(last_avg):
        print("Warning: Last average is NaN, setting to 0.")
        last_avg = 0

    forecasts = []

    for i in range(num_months):
        next_month = (monthly_data["month"].iloc[-1] + i + 1) % 12 or 12
        trend_factor = 1 + avg_trends.get(next_month, 0)
        if pd.isna(trend_factor):
            print(f"Warning: Trend factor is NaN for month {next_month}, setting to 1.")
            trend_factor = 1
        next_avg = last_avg * trend_factor if last_avg != 0 else 0
        forecasts.append(next_avg)
        last_avg = next_avg

    return forecasts


def forecast_all_parameters_simple(api_url_base, latitude, longitude):
    parameter_dfs = fetch_data(api_url_base, latitude, longitude)
    forecasts = {}
    for parameter, df in parameter_dfs.items():
        monthly_data = clean_and_analyze_t2m_data(df.rename(columns={parameter: "t2m"}))
        forecasted_values = forecast_with_trends(monthly_data)
        forecasts[parameter] = forecasted_values
    return forecasts


def calculate_water_cost_trend(forecasts):
    trend = []
    for i in range(4):
        deficit = forecasts["PRECTOTCORR"][i] - forecasts["EVPTRNS"][i]
        humidity_variation = forecasts["GWETROOT"][i] - forecasts["GWETTOP"][i]
        climate_impact = forecasts["T2M"][i]
        value = 0.5 * deficit + 0.3 * humidity_variation + 0.2 * climate_impact
        trend.append(value)
    return trend


def calculate_solar_energy_efficiency(forecasts):
    efficiency = []
    for i in range(4):
        value = (
            0.5 * forecasts["ALLSKY_SFC_SW_DWN"][i]
            + 0.3 * forecasts["ALLSKY_SFC_SW_DIFF"][i]
            + 0.2 * forecasts["CLRSKY_SFC_SW_DNI"][i]
        )
        efficiency.append(value)
    return efficiency


def calculate_climate_risk_trend(forecasts):
    risk = []
    for i in range(4):
        value = (
            0.4 * forecasts["PRECTOTCORR"][i]
            + 0.3 * forecasts["ALLSKY_SFC_SW_DWN"][i]
            + 0.3 * forecasts["WS10M"][i]
        )
        risk.append(value)
    return risk


analysis_type_map = {
    "Water Cost Trend": "Tendência do Custo Hídrico",
    "Solar Energy Efficiency": "Eficiência Energética Solar",
    "Infrastructure Climate Risk Trend": "Tendência de Risco Climático para Infraestruturas",
    "Air Quality Forecast": "Previsão da Qualidade do Ar",
}


def calculate_air_quality_forecast(forecasts):
    air_quality = []
    for i in range(4):
        value = (
            0.4 * forecasts["CLRSKY_DAYS"][i]
            + 0.3 * forecasts["ALLSKY_SFC_SW_DIFF"][i]
            + 0.3 * forecasts["CLRSKY_KT"][i]
        )
        air_quality.append(value)
    return air_quality


def calculate_topic_forecasts_with_text(parameter_forecasts):
    return {
        "Water Cost Trend": calculate_water_cost_trend(parameter_forecasts),
        "Solar Energy Efficiency": calculate_solar_energy_efficiency(
            parameter_forecasts
        ),
        "Infrastructure Climate Risk Trend": calculate_climate_risk_trend(
            parameter_forecasts
        ),
        "Air Quality Forecast": calculate_air_quality_forecast(parameter_forecasts),
    }


def fix_infinite_values(data):
    for i in range(len(data)):
        if data[i] == -float("inf"):
            if i > 0:
                data[i] = data[i - 1] * 1.2
            else:
                data[i] = 0
    return data


def llm_generate_insight(
    analysis_type,
    forecast_values,
    business_type,
    location,
    search_objective,
    main_problems,
):
    import google.generativeai as genai

    prompt = f"""
    Me ajude a ter alguns insights. A seguir, irei te passar alguns parâmetros da minha empresa e objetos
    Para {analysis_type}, eu sei que os próximos 4 meses terão as seguintes médias de tendência na variação
    {forecast_values}
    Minha empresa é do ramo: {business_type}
    Pense com base na minha localização Latitude {location['latitude']}, Longitude {location['longitude']}
    Meu objetivo de busca é: {search_objective}
    Os principais problemas de negócio que possuo são: {main_problems}

    Poderia me dar um insight ou recomendação de qual ação devo tomar, com base nos meus problemas, objetivos e todo o contexto? claro e objetivo com até 200 caracteres, priorizando informações úteis e acionáveis.
    Por favor, me responda em 2 frases apenas."""
    genai.configure(api_key=api_google_genai)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    resposta = (
        response.text.replace("Resposta:", "")
        .replace("\n", " ")
        .replace("/", "")
        .strip()
    )
    return resposta


def process_weather_forecast(input_json):
    api_url_base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    latitude = input_json["location"]["latitude"]
    longitude = input_json["location"]["longitude"]
    business_name = input_json["business_name"]
    business_type = input_json["business_type"]
    user_analysis_types = input_json["analysis_type"]
    search_objective = input_json["search_objective"]
    main_problems = input_json["main_problems"]

    parameter_forecasts = forecast_all_parameters_simple(
        api_url_base, latitude, longitude
    )
    topic_forecasts = calculate_topic_forecasts_with_text(parameter_forecasts)

    filtered_forecasts = {
        analysis_type_map[key]: fix_infinite_values(value)
        for key, value in topic_forecasts.items()
        if analysis_type_map[key] in user_analysis_types
    }

    output = {
        "business_name": business_name,
        "business_type": business_type,
        "insights": [],
    }

    for user_type, forecast_values in filtered_forecasts.items():
        graph_data = generate_graph_data(forecast_values, user_type)
        insight_tip = llm_generate_insight(
            analysis_type=user_type,
            forecast_values=forecast_values,
            business_type=business_type,
            location={"latitude": latitude, "longitude": longitude},
            search_objective=search_objective,
            main_problems=main_problems,
        )
        output["insights"].append(
            {
                "analysis_type": user_type,
                "graph_data": graph_data,
                "insight_tip": insight_tip,
            }
        )

    return output


def generate_graph_data(forecast_values, analysis_type):
    labels = ["January", "February", "March", "April"]
    label_map = {
        "Tendência do Custo Hídrico": "Tendência do Custo Hídrico",
        "Eficiência Energética Solar": "Eficiência Energética Solar",
        "Tendência de Risco Climático para Infraestruturas": "Infrastructure Climate Risk Trend",
        "Previsão da Qualidade do Ar": "Previsão da Qualidade do Ar",
    }
    return {
        "labels": labels,
        "datasets": {
            "label": label_map.get(analysis_type, analysis_type),
            "data": forecast_values,
        },
    }
