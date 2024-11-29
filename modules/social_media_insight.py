import requests
import time
import google.generativeai as genai
import urllib.parse
import unicodedata
import re
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://graph.instagram.com/v21.0"
api_google_genai = os.getenv("API_GOOGLE_GENAI_SMI")
instagram_business_id = os.getenv("INSTAGRAM_BUSINESS_ID")
access_token = os.getenv("ACCESS_TOKEN")

genai.configure(api_key=api_google_genai)
model = genai.GenerativeModel("gemini-1.5-flash")

DISCLAIMER = "\n\n🤖 Aviso: Todas as imagens e as notícias foram geradas com inteligência artificial com base em dados climáticos reais."


def generate_caption(data_json):
    prompt = (
        "Com base nos dados climáticos a seguir, elabore uma notícia destinada ao público urbano sobre os impactos atuais e futuros das tendências identificadas. A notícia deve: Ser escrita em linguagem clara e acessível ao público em geral. Destacar os principais insights, como aumento do custo hídrico, eficiência energética solar, risco climático para infraestruturas e previsão da qualidade do ar. Incluir informações específicas dos dados fornecidos, como números, porcentagens e tendências observadas. Oferecer dicas práticas sobre como a população pode mitigar esses impactos ou se adaptar a eles. Evitar lacunas, placeholders ou referências a inserir dados posteriormente. Não mencionar detalhes empresariais internos; foque nos impactos para a população urbana. O texto gerado só pode ter no máximo 2200 caracteres. Não utilizar asteriscos "
        " ou qualquer formatação especial no texto; escreva o texto normalmente sem indicações de negrito ou itálico **. Segue os dados para análise"
        f"{data_json}"
    )
    response = model.generate_content(prompt)
    caption = response.text.strip()
    return caption


def remover_acentos_e_pontuacao(texto):

    nfkd = unicodedata.normalize("NFKD", texto)
    texto_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])

    texto_limpo = re.sub(r"[^\w\s]", "", texto_sem_acento)
    return texto_limpo


def generate_image(caption):
    prompt = (
        "Responda de forma direta o que será solicitado, seu output deve ser somente o prompt. "
        "Crie um prompt para que a IA generativa Pollinations faça uma imagem para a seguinte notícia: "
        f"{caption}"
    )
    response = model.generate_content(prompt)

    if not hasattr(response, "text") or not response.text:
        print("Erro ao gerar prompt para a imagem:", response)
        return None

    response_prompt = response.text.strip()

    prompt_limpo = remover_acentos_e_pontuacao(response_prompt)

    encoded_prompt = urllib.parse.quote(prompt_limpo)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"

    img_response = requests.get(url)

    if img_response.status_code == 200:
        print("Imagem gerada com sucesso.")
        return img_response.url
    else:
        print("Erro ao gerar imagem:", img_response.text)
        return None


def fix_url(url):
    import urllib.parse

    url = url.replace("\\", "")

    parsed = urllib.parse.urlparse(url)

    prompt_path = parsed.path
    if prompt_path.startswith("/prompt/"):
        prompt_encoded = prompt_path[len("/prompt/") :]

        prompt_encoded = prompt_encoded.replace("u0025", "%")

        prompt_decoded = urllib.parse.unquote(prompt_encoded)

        prompt_fixed = prompt_decoded.replace("%", "/u0025")

        new_path = "/prompt/" + prompt_fixed
        new_url = urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                new_path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
        return new_url
    else:
        return url


def verify_image_url(url):
    try:
        response = requests.head(url)
        if response.status_code == 200 and "image" in response.headers.get(
            "Content-Type", ""
        ):
            print("URL da imagem verificada com sucesso.")
            return True
        else:
            print("URL da imagem inválida ou inacessível:", response.status_code)
            return False
    except requests.RequestException as e:
        print("Erro ao verificar a URL da imagem:", e)
        return False


def create_media_container(img_url, caption):
    url = f"{BASE_URL}/{instagram_business_id}/media"
    print({img_url})
    payload = {"image_url": img_url, "caption": caption, "access_token": access_token}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        media_id = response.json().get("id")
        print(f"Container de mídia criado: {media_id}")
        return media_id
    else:
        print("Erro ao criar container de mídia:", response.text)
        return None


def publish_media(media_id):
    url = f"{BASE_URL}/{instagram_business_id}/media_publish"
    payload = {"creation_id": media_id, "access_token": access_token}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        post_id = response.json().get("id")
        print(f"Post publicado com ID: {post_id}")
        return post_id
    else:
        print("Erro ao publicar mídia:", response.text)

        return None


def check_publishing_status(container_id):
    url = f"{BASE_URL}/{container_id}"
    params = {"fields": "status_code", "access_token": access_token}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        status = response.json().get("status_code")
        print(f"Status do contêiner: {status}")
        return status
    else:
        print("Erro ao verificar status do contêiner:", response.text)
        return None


def generate_social_media_insight(data_json):

    original_caption = generate_caption(data_json)
    print("Legenda gerada:", original_caption)

    caption = original_caption + DISCLAIMER
    print("Legenda final:", caption)

    img_url = generate_image(original_caption)
    if not img_url:
        print("Falha ao gerar a imagem. Encerrando o processo.")
        return

    if not verify_image_url(img_url):
        print("URL da imagem inválida. Encerrando o processo.")
        return

    media_id = create_media_container(img_url, caption)
    if not media_id:
        print("Falha ao criar o container de mídia. Encerrando o processo.")
        return

    time.sleep(5)

    post_id = publish_media(media_id)
    if not post_id:
        print("Falha ao publicar a mídia. Verificando status do contêiner.")
        status = check_publishing_status(media_id)
        if status:
            if status == "FINISHED":
                post_id = publish_media(media_id)
                if post_id:
                    print(f"Post publicado com ID: {post_id}")
            elif status in ["ERROR", "EXPIRED"]:
                print(f"Não foi possível publicar o contêiner. Status: {status}")
            elif status == "IN_PROGRESS":
                print(
                    "A publicação ainda está em andamento. Tente novamente mais tarde."
                )
            elif status == "PUBLISHED":
                print("O contêiner já foi publicado.")
        return

    return post_id
