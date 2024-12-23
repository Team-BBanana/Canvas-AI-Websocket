import openai
import faster_whisper, os
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
from dotenv import load_dotenv 
import asyncio
import websockets
import io

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

# OpenAI 텍스트 생성 함수
def generate(messages):
    global answer
    answer = ""        
    for chunk in openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, stream=True):
        # delta와 content 유효성 확인
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            text_chunk = delta.content
            answer += text_chunk
            print(text_chunk, end="", flush=True)  # 실시간으로 텍스트 출력
            yield text_chunk
        else:
            # delta.content가 없거나 비어 있을 경우 처리
            print("No content in this chunk")


# 음성 파일을 텍스트로 변환
def text_transform(audio_file_path, language="ko"):
    return " ".join(seg.text for seg in model.transcribe(audio_file_path, language=language)[0])

# 응답 생성 및 음성 파일로 변환
def generate_response(system_prompt, history):
    user_text = text_transform("received_voice.wav")  # 음성 파일 처리
    print(f'>>>{user_text}\n<<< ', end="", flush=True)
    history.append({'role': 'user', 'content': user_text})

    # OpenAI 응답 생성
    generator = generate([system_prompt] + history[-10:])
    
    # ElevenLabs로 텍스트 음성 변환
    audio_stream = elevenlabs_client.generate(text=generator, voice="Aria", model="eleven_multilingual_v2", stream=True)

    # 음성을 바이트로 변환
    audio_data = io.BytesIO()
    for audio_chunk in audio_stream:
        audio_data.write(audio_chunk)
    
    audio_data.seek(0)  # 파일 포인터를 맨 앞으로 이동
    return audio_data

# 클라이언트로 파일 받기
async def handle_client(websocket, path=None):
        # 클라이언트로부터 오디오 파일 받기
        audio_data = await websocket.recv()
        with open("received_voice.wav", "wb") as f:
            f.write(audio_data)
        print("음성 파일이 성공적으로 저장되었습니다.")
        
        # 파일 저장 후 텍스트 생성 및 음성으로 변환
        audio_response = generate_response(system_prompt, history)

        # 음성을 바이트 스트림으로 반환
        audio_bytes = audio_response.read()
        
        print(f"음성 데이터 길이: {len(audio_bytes)}")  # 받은 음성 데이터의 크기를 확인
        
        # 변환된 음성을 클라이언트에 전송
        await websocket.send(audio_bytes)
        print("음성 응답이 클라이언트로 전송되었습니다.")


# 웹소켓 서버 실행
async def start_server():
    server = await websockets.serve(handle_client, "localhost", 8765)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_server())
