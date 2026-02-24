-- Update managing_body for 국가공인 민간자격 (부분 매칭 기반)
-- 안전하게 실행 가능: 이름이 없는 경우에는 아무 행도 업데이트되지 않습니다.

-- (사)대한민국한자교육연구회
UPDATE qualification
SET managing_body = '(사)대한민국한자교육연구회'
WHERE qual_name LIKE '한자·한문전문지도사%' OR qual_name LIKE '한자·한문전문지도사(%';

UPDATE qualification
SET managing_body = '(사)대한민국한자교육연구회'
WHERE qual_name LIKE '한자급수자격검정%' OR qual_name LIKE '한자급수자격검정(%';

-- (사)대한병원행정관리자협회
UPDATE qualification
SET managing_body = '(사)대한병원행정관리자협회'
WHERE qual_name LIKE '병원행정사%';

-- (사)범국민예의생활실천운동본부
UPDATE qualification
SET managing_body = '(사)범국민예의생활실천운동본부'
WHERE qual_name LIKE '실천예절지도사%';

-- (사)신용정보협회
UPDATE qualification
SET managing_body = '(사)신용정보협회'
WHERE qual_name LIKE '신용관리사%';

-- (사)한국경비협회
UPDATE qualification
SET managing_body = '(사)한국경비협회'
WHERE qual_name LIKE '신변보호사%';

-- (사)한국국어능력평가협회
UPDATE qualification
SET managing_body = '(사)한국국어능력평가협회'
WHERE qual_name LIKE '한국실용글쓰기검정%';

-- (사)한국금융연수원
UPDATE qualification
SET managing_body = '(사)한국금융연수원'
WHERE qual_name LIKE 'CRA(신용위험분석사)%'
   OR qual_name LIKE '국제금융역%'
   OR qual_name LIKE '신용분석사%'
   OR qual_name LIKE '여신심사역%'
   OR qual_name LIKE '외환전문역%'
   OR qual_name LIKE '자산관리사%';

-- (사)한국농아인협회
UPDATE qualification
SET managing_body = '(사)한국농아인협회'
WHERE qual_name LIKE '수화통역사%';

-- (사)한국분재조합
UPDATE qualification
SET managing_body = '(사)한국분재조합'
WHERE qual_name LIKE '분재관리사%';

-- (사)한국소프트웨어저작권협회
UPDATE qualification
SET managing_body = '(사)한국소프트웨어저작권협회'
WHERE qual_name LIKE '소프트웨어자산관리사%';

-- (사)한국수목보호협회
UPDATE qualification
SET managing_body = '(사)한국수목보호협회'
WHERE qual_name LIKE '수목보호기술자%';

-- (사)한국시각장애인연합회
UPDATE qualification
SET managing_body = '(사)한국시각장애인연합회'
WHERE qual_name LIKE '보행지도사%'
   OR qual_name LIKE '점역교정사%';

-- (사)한국애견협회
UPDATE qualification
SET managing_body = '(사)한국애견협회'
WHERE qual_name LIKE '반려견스타일리스트%';

-- (사)한국어문회
UPDATE qualification
SET managing_body = '(사)한국어문회'
WHERE qual_name LIKE '한자능력급수%';

-- (사)한국에너지기술인협회
UPDATE qualification
SET managing_body = '(사)한국에너지기술인협회'
WHERE qual_name LIKE '지역난방설비관리사%';

-- (사)한국열쇠협회
UPDATE qualification
SET managing_body = '(사)한국열쇠협회'
WHERE qual_name LIKE '열쇠관리사%';

-- (사)한국원가관리협회
UPDATE qualification
SET managing_body = '(사)한국원가관리협회'
WHERE qual_name LIKE '원가분석사%';

-- (사)한국자동차진단보증협회
UPDATE qualification
SET managing_body = '(사)한국자동차진단보증협회'
WHERE qual_name LIKE '자동차진단평가사%';

-- (사)한국정보관리협회
UPDATE qualification
SET managing_body = '(사)한국정보관리협회'
WHERE qual_name LIKE '한자어능력%';

-- (사)한국정보통신자격협회
UPDATE qualification
SET managing_body = '(사)한국정보통신자격협회'
WHERE qual_name LIKE 'PC정비사%'
   OR qual_name LIKE '네트워크관리사%'
   OR qual_name LIKE '영상정보관리사%'
   OR qual_name LIKE '지능형홈관리사%';

-- (사)한국정보통신진흥협회
UPDATE qualification
SET managing_body = '(사)한국정보통신진흥협회'
WHERE qual_name LIKE '디지털정보활용능력(DIAT)%'
   OR qual_name LIKE '리눅스마스터%'
   OR qual_name LIKE '인터넷정보관리사%';

-- (사)한국정보평가협회
UPDATE qualification
SET managing_body = '(사)한국정보평가협회'
WHERE qual_name LIKE 'CS Leaders(관리사)%'
   OR qual_name LIKE 'PC Master(정비사)%';

-- (사)한국정보화진흥원
UPDATE qualification
SET managing_body = '(사)한국정보화진흥원'
WHERE qual_name LIKE '정보시스템감리사%';

-- (사)한국조경수협회
UPDATE qualification
SET managing_body = '(사)한국조경수협회'
WHERE qual_name LIKE '조경수조성관리사%';

-- (사)한국종이접기협회
UPDATE qualification
SET managing_body = '(사)한국종이접기협회'
WHERE qual_name LIKE '종이접기마스터%';

-- (사)한국주거학회
UPDATE qualification
SET managing_body = '(사)한국주거학회'
WHERE qual_name LIKE '주거복지사%';

-- (사)한국지능형사물인터넷협회
UPDATE qualification
SET managing_body = '(사)한국지능형사물인터넷협회'
WHERE qual_name LIKE 'RFID기술자격검정%';

-- (사)한국직업연구진흥원
UPDATE qualification
SET managing_body = '(사)한국직업연구진흥원'
WHERE qual_name LIKE '샵마스터%';

-- (사)한국창의인성교육연구원
UPDATE qualification
SET managing_body = '(사)한국창의인성교육연구원'
WHERE qual_name LIKE 'E-TEST Professionals%'
   OR qual_name LIKE '실용수학%';

-- (사)한국평생교육평가원
UPDATE qualification
SET managing_body = '(사)한국평생교육평가원'
WHERE qual_name LIKE '한국영어검정(TESL)%'
   OR qual_name LIKE '한국한자검정%';

-- (사)한국포렌식학회/한국인터넷진흥원
UPDATE qualification
SET managing_body = '(사)한국포렌식학회/한국인터넷진흥원'
WHERE qual_name LIKE '디지털포렌식전문가%';

-- (사)한국행정관리협회
UPDATE qualification
SET managing_body = '(사)한국행정관리협회'
WHERE qual_name LIKE '행정관리사%';

-- (사)한자교육진흥회
UPDATE qualification
SET managing_body = '(사)한자교육진흥회'
WHERE qual_name LIKE '한자·한문지도사%'
   OR qual_name LIKE '한자실력급수%';

-- (재)서울대학교발전기금
UPDATE qualification
SET managing_body = '(재)서울대학교발전기금'
WHERE qual_name LIKE 'TEPS(영어능력검정)%';

-- (재)한국데이터진흥원
UPDATE qualification
SET managing_body = '(재)한국데이터진흥원'
WHERE qual_name LIKE 'SQL(%'
   OR qual_name LIKE '데이터분석전문가%'
   OR qual_name LIKE '데이터분석준전문가%'
   OR qual_name LIKE '데이터아키텍처전문가%';

-- (주)피씨티
UPDATE qualification
SET managing_body = '(주)피씨티'
WHERE qual_name LIKE 'PC활용능력평가시험(PCT)%';

-- KBS한국방송공사
UPDATE qualification
SET managing_body = 'KBS한국방송공사'
WHERE qual_name LIKE 'KBS한국어능력시험%';

-- KT
UPDATE qualification
SET managing_body = 'KT'
WHERE qual_name LIKE 'AICE(AI CERTIFICATE FOR EVERYONE)%';

-- 국제뇌교육종합대학원대학교
UPDATE qualification
SET managing_body = '국제뇌교육종합대학원대학교'
WHERE qual_name LIKE '브레인트레이너%';

-- 대한상공회의소
UPDATE qualification
SET managing_body = '대한상공회의소'
WHERE qual_name LIKE 'FLEX %'
   OR qual_name LIKE '무역영어%'
   OR qual_name LIKE '상공회의소 IT +%'
   OR qual_name LIKE '상공회의소 한자%';

-- 대한정보통신기술(합)
UPDATE qualification
SET managing_body = '대한정보통신기술(합)'
WHERE qual_name LIKE '정보기술프로젝트관리전문가(IT-PMP)%';

-- 도로교통공단
UPDATE qualification
SET managing_body = '도로교통공단'
WHERE qual_name LIKE '도로교통사고감정사%';

-- 매일경제신문사
UPDATE qualification
SET managing_body = '매일경제신문사'
WHERE qual_name LIKE '경제금융이해력인증시험(틴매경 TEST)%'
   OR qual_name LIKE '매경TEST%';

-- 사단법인 보험연수원
UPDATE qualification
SET managing_body = '사단법인 보험연수원'
WHERE qual_name LIKE '개인보험심사역%'
   OR qual_name LIKE '기업보험심사역%';

-- 삼일회계법인
UPDATE qualification
SET managing_body = '삼일회계법인'
WHERE qual_name LIKE '재경관리사%'
   OR qual_name LIKE '회계관리%';

-- 신용회복위원회
UPDATE qualification
SET managing_body = '신용회복위원회'
WHERE qual_name LIKE '신용상담사%';

-- 한국경제신문
UPDATE qualification
SET managing_body = '한국경제신문'
WHERE qual_name LIKE '경제이해력검증시험(TESAT)%'
   OR qual_name LIKE '청소년경제이해력검증시험(J-TESAT)%';

-- 한국공인회계사회
UPDATE qualification
SET managing_body = '한국공인회계사회'
WHERE qual_name LIKE 'AT자격시험(FAT1,2급, TAT1,2급)%';

-- 한국냉동공조산업협회
UPDATE qualification
SET managing_body = '한국냉동공조산업협회'
WHERE qual_name LIKE '시스템에어컨설계시공관리사%';

-- 한국농어촌공사
UPDATE qualification
SET managing_body = '한국농어촌공사'
WHERE qual_name LIKE '농어촌개발컨설턴트%';

-- 한국발명진흥회
UPDATE qualification
SET managing_body = '한국발명진흥회'
WHERE qual_name LIKE '지식재산능력시험%';

-- 한국산업기술보호협회
UPDATE qualification
SET managing_body = '한국산업기술보호협회'
WHERE qual_name LIKE '산업보안관리사%';

-- 한국생산성본부
UPDATE qualification
SET managing_body = '한국생산성본부'
WHERE qual_name LIKE 'ERP물류정보관리사%'
   OR qual_name LIKE 'ERP생산정보관리사%'
   OR qual_name LIKE 'ERP인사정보관리사%'
   OR qual_name LIKE 'ERP회계정보관리사%'
   OR qual_name LIKE 'GTQ(그래픽기술자격)%'
   OR qual_name LIKE 'GTQi(그래픽기술자격일러스트)%'
   OR qual_name LIKE 'IEQ(인터넷윤리자격)%'
   OR qual_name LIKE 'SMAT서비스경영자격%'
   OR qual_name LIKE '정보기술자격(ITQ)시험%';

-- 한국세무사회
UPDATE qualification
SET managing_body = '한국세무사회'
WHERE qual_name LIKE '세무회계%'
   OR qual_name LIKE '전산세무회계%';

-- 한국실내건축가협회
UPDATE qualification
SET managing_body = '한국실내건축가협회'
WHERE qual_name LIKE '실내디자이너%';

-- 한국옥외광고협회
UPDATE qualification
SET managing_body = '한국옥외광고협회'
WHERE qual_name LIKE '옥외광고사%';

-- 한국원산지정보원
UPDATE qualification
SET managing_body = '한국원산지정보원'
WHERE qual_name LIKE '원산지관리사%';

-- 한국의료기기안전정보원
UPDATE qualification
SET managing_body = '한국의료기기안전정보원'
WHERE qual_name LIKE '의료기기RA전문가%';

-- 한국정보통신기술협회
UPDATE qualification
SET managing_body = '한국정보통신기술협회'
WHERE qual_name LIKE 'SW테스트전문가(CSTS)%';

