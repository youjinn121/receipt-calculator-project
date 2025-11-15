import requests
import uuid
import time
import json
import os 
from dotenv import load_dotenv 

# .env 파일 로드
load_dotenv()

# .env 파일에서 값 불러오기
api_url = os.getenv("CLOVA_OCR_API_URL")
secret_key = os.getenv("CLOVA_OCR_SECRET_KEY")


def process_receipt_ocr(image_path):
    """
    지정된 영수증 이미지 파일을 받아 OCR API를 호출하고,
    결과 JSON을 파일로 저장한 뒤 데이터를 반환하는 함수
    """
    
    # 1. 파일 존재 여부 확인 (가장 먼저 체크)
    if not os.path.exists(image_path):
        print(f"❌ 오류: 파일 '{image_path}'을(를) 찾을 수 없습니다.")
        return None 

    # 2. 파일 이름과 확장자 분리
    image_file = image_path
    image_format = image_file.split('.')[-1].lower() # 확장자 (jpg, png 등)
    
    # 3. 출력 파일 이름 만들기 
    base_name = os.path.splitext(image_file)[0]
    output_file = f"{base_name}_result.json"

    # 4. 요청 데이터 구성
    request_json = {
        'images': [{'format': image_format, 'name': base_name}],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    # 5. API 호출 준비
    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [('file', open(image_file, 'rb'))]
    headers = {'X-OCR-SECRET': secret_key}

    print(f"\n'{image_file}' 처리 중... (API 호출)")
    
    # 6. API 호출 및 응답 처리
    try:
        response = requests.request("POST", api_url, headers=headers, data=payload, files=files)
        response.raise_for_status() 

        result_data = response.json() 
        
        # [저장 로직] 결과를 JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
            
        print(f"✅ [저장 완료] 결과가 '{output_file}'에 저장되었습니다.")
        
        return result_data

    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 중 오류 발생: {e}")
        if e.response is not None and e.response.content:
            print(f"상세 오류 메시지: {e.response.text}")
        return None 


# 메인 실행 블록]
if __name__ == "__main__":
    
    # 처리하고 싶은 파일 이름들을 넣기
    receipt_files = [
        "emart_1.jpg"
        # 나중에 추가 예시: "receipt_2.png", "mart_receipt.jpg" 
    ] 
    
    print(f"--- 총 {len(receipt_files)}개의 파일 처리를 시작합니다 ---")

    for receipt_file in receipt_files:
        # 함수 호출
        ocr_result = process_receipt_ocr(receipt_file)
        
        if ocr_result:
            print(f"'{receipt_file}' 처리 성공!")
            
            # [다음 단계] 
            # 여기서 ocr_result 데이터를 이용해 상품명/가격을 추출하는 코드가 들어갑니다.
            
        else:
            print(f"'{receipt_file}' 처리 실패.")
            
    print("\n--- 모든 작업 완료 ---")