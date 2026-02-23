import os
import logging
import orjson
import redis
from quixstreams import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quix_worker")

def start_quix_pipeline():
    """
    Quix Streams를 사용하여 자격증 데이터가 변경되면 
    즉시 Redis를 갱신(Sink)하는 파이프라인 (안티그래비티 극초저지연)
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(redis_url)

    # 브로커가 세팅되어 있지 않다면 기본 로컬호스트
    kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    
    # Quix Application 초기화
    # 인위적인 지연을 극단적으로 피하기 위해 가벼운 consumer_group 설정
    app = Application(
        broker_address=kafka_broker,
        consumer_group="cert_fast_sync_group",
        auto_offset_reset="latest"
    )

    # 토픽 설정: orjson 역직렬화, 혹은 기본 json (이 예제에서는 기본 JSON 데시리얼라이저 혹은 직접 처리)
    cert_topic = app.topic("cert_updates")

    # 스트림 데이터프레임
    sdf = app.dataframe(cert_topic)

    # 데이터 가공 최소화 & Redis 신속 적재
    def fast_redis_sink(data: dict):
        try:
            cert_id = data.get("qual_id")
            if cert_id:
                # 불필요한 메시지 없이 {"status":"success", "data":{...}} 구조
                payload = {"status": "success", "data": data}
                
                # orjson을 이용한 극히 빠른 직렬화 -> bytes
                val_bytes = orjson.dumps(payload)
                
                # Redis 덮어쓰기 (네트워크 지연을 감안해도 ms 단위)
                r.set(f"fastcert:{cert_id}", val_bytes)
                logger.info(f"Redis updated instantly for cert {cert_id}")
        except Exception as e:
            logger.error(f"Sink error: {e}")
            
        # 다음 파이프라인(있다면)으로 데이터 연장
        return data

    # 스트림에 싱크 함수 적용 (Apply)
    sdf = sdf.apply(fast_redis_sink)

    logger.info("Quix Streams ultra-low latency pipeline started.")
    
    # Application 실행
    try:
        app.run(sdf)
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")

if __name__ == "__main__":
    start_quix_pipeline()
