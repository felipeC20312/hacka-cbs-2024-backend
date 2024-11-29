from flask_cors import CORS
from flasgger import Swagger
from flask import Flask, request
from modules.weather_forecast import process_weather_forecast
from modules.social_media_insight import generate_social_media_insight

app = Flask(__name__)
swagger = Swagger(app)

allowed_origins = [
    "http://localhost:5173",
    "https://hacka-cbs-2024-backend.onrender.com",
]
CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)


@app.route("/")
def home():
    """Página inicial da API
    ---
    responses:
      200:
        description: Retorna a página inicial da API
        schema:
          type: string
          example: "Api home page documentations"
    """
    return "Api home page documentations"


@app.route("/healthCheck", methods=["GET"])
def healthCheck():
    """Verificação de Saúde da API
    ---
    responses:
      200:
        description: Confirma que a API está respondendo como esperado
        schema:
          type: string
          example: "Health check done, api is responding as expected"
    """
    return "Health check done, api is responding as expected", 200


@app.route("/process_weather_forecasting", methods=["POST"])
def processWeatherForecasting():
    """Processa a análise empresarial
    ---
    parameters:
      - in: body
        name: input_json
        description: JSON contendo dados para a análise empresarial
        required: true
        schema:
          type: object
          properties:
            business_name:
              type: string
              example: "Teste LTDA"
            business_type:
              type: string
              example: "têxtil"
            location:
              type: object
              properties:
                latitude:
                  type: number
                  example: -14.819536302850208
                longitude:
                  type: number
                  example: -57.457759772352226
            analysis_type:
              type: array
              items:
                type: string
              example: [
                "Tendência do Custo Hídrico",
                "Eficiência Energética Solar",
                "Tendência de Risco Climático para Infraestruturas",
                "Previsão da Qualidade do Ar"
              ]
            search_objective:
              type: string
              example: "Reduzir custos operacionais relacionados ao consumo de água e energia."
            main_problems:
              type: string
              example: "Escassez hídrica em períodos críticos e altos custos de energia elétrica."
    responses:
      200:
        description: Resultados da análise empresarial
        schema:
          type: string
    """
    data_json = request.get_json()
    return process_weather_forecast(data_json)


@app.route("/generate_social_media_insigth", methods=["POST"])
def generateSocialMediaInsigth():
    """Processa múltiplas análises e insights
    ---
    parameters:
      - in: body
        name: insights_json
        description: JSON contendo dados de análises, gráficos e insights empresariais
        required: true
        schema:
          type: object
          properties:
            business_name:
              type: string
              example: "Teste LTDA"
            business_type:
              type: string
              example: "têxtil"
            insights:
              type: array
              items:
                type: object
                properties:
                  analysis_type:
                    type: string
                    example: "Tendência do Custo Hídrico"
                  graph_data:
                    type: object
                    properties:
                      labels:
                        type: array
                        items:
                          type: string
                        example: ["January", "February", "March", "April"]
                      datasets:
                        type: object
                        properties:
                          label:
                            type: string
                            example: "Tendência do Custo Hídrico"
                          data:
                            type: array
                            items:
                              type: number
                            example: [13.76, 15.66, 18.79, 22.55]
                  insight_tip:
                    type: string
                    example: "Implemente imediatamente medidas de eficiência hídrica (reúso, vazamentos) e energia (iluminação LED, motores eficientes). Acompanhe a tendência de custos hídricos para ajustes estratégicos nos próximos meses."
    responses:
      200:
        description: Resultados das análises e insights
        schema:
          type: string
    """
    data_json = request.get_json()
    return generate_social_media_insight(data_json)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
