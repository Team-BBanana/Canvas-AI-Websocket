# Python 3.10을 기반으로 하는 공식 이미지 사용
FROM python:3.10-slim

# 컨테이너 내 작업 디렉토리 설정
WORKDIR /app

# ARG 선언
ARG OPENAI_API_KEY
ARG ELEVEN_API_KEY

# 환경 변수로 설정
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV ELEVEN_API_KEY=${ELEVEN_API_KEY}

# 필수 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 로컬의 requirements.txt 파일을 컨테이너로 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 로컬의 voice_talk.py 파일을 컨테이너로 복사
COPY voice_talk.py .

# 컨테이너 시작 시 실행될 명령어 정의
CMD ["python", "voice_talk.py"]