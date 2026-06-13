import streamlit as st
import googleapiclient.discovery
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import konlpy
from konlpy.tag import Okt
import os

# 1. 유튜브 API를 이용한 댓글 수집 함수
def get_youtube_comments(video_url, api_key):
    # 영상 ID 추출 (일반 링크 및 모바일 share 링크 대응)
    video_id_match = re.search(r'(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})', video_url)
    if not video_id_match:
        st.error("올바른 유튜브 URL을 입력해주세요.")
        return []
    
    video_id = video_id_match.group(1)
    
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    comments = []
    
    try:
        # 첫 페이지 댓글 가져오기 (최대 100개, 필요시 반복문으로 추가 가능)
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            textFormat="plainText"
        )
        response = request.execute()
        
        for item in response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
            
        return comments
    except Exception as e:
        st.error(f"유튜브 API 호출 중 오류가 발생했습니다: {e}")
        return []

# 2. 한글 형태소 분석 및 텍스트 정제 함수
def clean_and_tokenize(comments):
    okt = Okt()
    all_words = []
    
    # 분석에서 제외할 불용어(Stopwords) 설정
    stopwords = ['정말', '진짜', '너무', '영상', '보고', '완전', '클라우드', '유튜브', '댓글', '그냥', '이거', '분석']
    
    for comment in comments:
        # 한글과 공백만 남기기
        cleaned = re.sub(r'[^가-힣\s]', '', comment)
        # 명사만 추출
        nouns = okt.nouns(cleaned)
        # 2글자 이상이고 불용어에 포함되지 않는 단어만 필터링
        words = [word for word in nouns if len(word) > 1 and word not in stopwords]
        all_words.extend(words)
        
    return all_words

# 3. 스트림릿 UI 구성
st.set_page_config(page_title="유튜브 댓글 심층 분석기", layout="wide")
st.title("📊 유튜브 댓글 심층 분석 및 워드 클라우드")
st.write("유튜브 링크와 API 키를 입력하면 댓글을 분석하여 주요 키워드와 워드클라우드를 생성합니다.")

# 사이드바에서 API 키 및 링크 입력
st.sidebar.header("설정 (Settings)")
api_key = st.sidebar.text_input("YouTube API Key를 입력하세요", type="password")
video_url = st.sidebar.text_input("유튜브 영상 URL을 입력하세요")
submit_button = st.sidebar.button("댓글 분석 시작")

if submit_button:
    if not api_key or not video_url:
        st.warning("API Key와 유튜브 URL을 모두 입력해주세요.")
    else:
        with st.spinner("유튜브에서 댓글을 가져오는 중..."):
            comments = get_youtube_comments(video_url, api_key)
        
        if comments:
            st.success(f"성공적으로 {len(comments)}개의 댓글을 수집했습니다!")
            
            # 레이아웃 분할
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💬 수집된 댓글 샘플 (최근 5개)")
                for c in comments[:5]:
                    st.write(f"- {c}")
            
            with st.spinner("한글 형태소 분석 및 워드클라우드 생성 중..."):
                words = clean_and_tokenize(comments)
                
                if not words:
                    st.warning("분석할 수 있는 한글 명사 단어가 부족합니다.")
                else:
                    # 단어 빈도수 계산
                    word_counts = Counter(words)
                    top_words = word_counts.most_common(10)
                    
                    with col2:
                        st.subheader("🔝 가장 많이 언급된 단어 TOP 10")
                        for word, count in top_words:
                            st.write(f"**{word}**: {count}회")
                    
                    # --- 워드 클라우드 생성 ---
                    st.markdown("---")
                    st.subheader("☁️ 한글 워드 클라우드 결과")
                    
                    # 스트림릿 클라우드(리눅스환경)의 나눔 폰트 경로 설정
                    # 패키지에 포함된 기본 폰트나 리눅스 시스템 폰트를 타겟팅합니다.
                    font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
                    
                    # 만약 로컬(윈도우/맥) 테스트 환경일 경우 시스템 폰트 자동 적용 안전장치
                    if not os.path.exists(font_path):
                        font_path = "Malgun Gothic" if os.name == "nt" else "AppleGothic"
                    
                    try:
                        wordcloud = WordCloud(
                            font_path=font_path,
                            background_color='white',
                            width=800,
                            height=400,
                            max_words=100
                        ).generate_from_frequencies(word_counts)
                        
                        # Matplotlib 그리기
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='interpole')
                        ax.axis('off')
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"워드클라우드 생성 중 오류가 발생했습니다: {e}")
                        st.info("팁: 스트림릿 클라우드 배포 시 packages.txt에 fonts-nanum을 추가했는지 확인해주세요.")
