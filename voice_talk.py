import openai
import faster_whisper, os
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
from dotenv import load_dotenv 
import asyncio
import websockets

os.environ.clear()
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print("OPEN_API_KEY:", OPENAI_API_KEY)  # 확인용
ELEVEN_API_KEY = os.getenv('ELEVEN_API_KEY')

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# OpenAI 클라이언트 설정
openai.api_key = OPENAI_API_KEY

# ElevenLabs 클라이언트 설정
elevenlabs_client = ElevenLabs(api_key=ELEVEN_API_KEY)  # API 키를 인자로 전달

system_prompt = {
    'role': 'system',
    'content': '당신은 3~10세 어린이와 함께 친근하고 자연스러운 한국어로 대화하는 친구입니다. 어린이가 그림을 그리며 당신과 대화합니다. 짧고 친근한 대화를 합니다. 대답이 아닌 제안을 해줄 수도 있습니다. 귀엽고 발랄한 성격을 가지고 있습니다.'
}

model, answer, history = faster_whisper.WhisperModel(model_size_or_path="small", device='cpu'), "", []

def generate(messages):
    """
    OpenAI API를 사용하여 텍스트를 생성하는 함수
    :param messages: 시스템 프롬프트 및 대화 히스토리
    :return: 생성된 텍스트를 실시간으로 스트리밍
    """
    global answer
    answer = ""        
    for chunk in openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, stream=True):
        if (text_chunk := chunk.choices[0].delta.content):
            answer += text_chunk
            print(text_chunk, end="", flush=True)  # 실시간으로 텍스트 출력
            yield text_chunk

def text_transform(audio_file_path, language="ko"):
    """
    음성 파일을 텍스트로 변환하는 함수
    :param audio_file_path: 변환할 오디오 파일 경로
    :param language: 언어 코드 (기본: 한국어)
    :return: 변환된 텍스트
    """
    return " ".join(seg.text for seg in model.transcribe(audio_file_path, language=language)[0])

def generate_response(system_prompt, history):
    """
    시스템 프롬프트와 대화 히스토리를 바탕으로 텍스트를 생성하는 함수
    :param system_prompt: 시스템 프롬프트
    :param history: 대화 히스토리
    :return: 생성된 텍스트
    """
    # 사용자 입력 기록
    user_text = text_transform("received_voice.wav")  # 음성 파일 처리
    print(f'>>>{user_text}\n<<< ', end="", flush=True)
    history.append({'role': 'user', 'content': user_text})

    # 응답 생성
    generator = generate([system_prompt] + history[-10:])
    
    # 생성된 텍스트를 스트리밍
    stream(elevenlabs_client.generate(text=generator, voice="Nicole", model="eleven_multilingual_v2", stream=True))
    
    # 어시스턴트 응답 기록
    history.append({'role': 'assistant', 'content': generator})

# 클라이언트로부터 파일 받기
async def handle_client(websocket, path=None):
    try:
        # 클라이언트로부터 오디오 파일 받기
        audio_data = await websocket.recv()

        # 파일 저장
        with open("received_voice.wav", "wb") as f:
            f.write(audio_data)
        
        print("음성 파일이 성공적으로 저장되었습니다.")
        
        # 파일 저장 후 텍스트 생성 및 스트리밍
        generate_response(system_prompt, history)
    
    except Exception as e:
        print(f"파일 받기 오류: {e}")

# 웹소켓 서버 실행
async def start_server():
    server = await websockets.serve(handle_client, "localhost", 8765)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_server())