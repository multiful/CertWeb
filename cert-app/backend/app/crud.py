
"""CRUD operations for database models."""
from types import SimpleNamespace
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, or_, and_, text

from app.models import Qualification, QualificationStats, MajorQualificationMap, UserFavorite, UserAcquiredCert, Job, Major
from app.schemas import (
    QualificationCreate, QualificationUpdate,
    QualificationStatsCreate, QualificationStatsUpdate,
    MajorQualificationMapCreate
)


# ============== Qualification CRUD ==============

class QualificationCRUD:
    """CRUD operations for Qualification."""
    
    @staticmethod
    def get_by_id(db: Session, qual_id: int) -> Optional[Qualification]:
        """Get qualification by ID."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_qualification_by_id(qual_id)
            
        return db.query(Qualification).filter(Qualification.qual_id == qual_id).first()
    
    @staticmethod
    def get_with_stats(db: Session, qual_id: int) -> Optional[Qualification]:
        """Get qualification with stats."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_qual_with_stats(qual_id)
            
        return db.query(Qualification).options(
            joinedload(Qualification.stats),
            joinedload(Qualification.jobs)
        ).filter(Qualification.qual_id == qual_id).first()
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        main_field: Optional[str] = None,
        ncs_large: Optional[str] = None,
        qual_type: Optional[str] = None,
        managing_body: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort: str = "name",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 20,
        cached_total: Optional[int] = None,
    ) -> tuple[List[Qualification], int]:
        """Get paginated list of qualifications with filters. cached_total가 있으면 count() 생략."""
        query = db.query(Qualification)
        
        # Apply filters
        if q:
            query = query.filter(
                or_(
                    Qualification.qual_name.ilike(f"%{q}%"),
                    Qualification.managing_body.ilike(f"%{q}%")
                )
            )
        
        if main_field:
            query = query.filter(Qualification.main_field == main_field)
        
        if ncs_large:
            query = query.filter(Qualification.ncs_large == ncs_large)
        
        if qual_type:
            query = query.filter(Qualification.qual_type == qual_type)
        
        if managing_body:
            query = query.filter(Qualification.managing_body == managing_body)
        
        if is_active is not None:
            query = query.filter(Qualification.is_active == is_active)
        
        if cached_total is not None:
            total = cached_total
        else:
            total = query.count()
        
        # Apply sorting
        if sort == "name":
            query = query.order_by(desc(Qualification.qual_name) if sort_desc else asc(Qualification.qual_name))
        elif sort == "recent":
            query = query.order_by(desc(Qualification.created_at) if sort_desc else asc(Qualification.created_at))
        elif sort in ["pass_rate", "difficulty"]:
            # stats 조인 후 그룹 집계로 정렬
            query = query.outerjoin(QualificationStats).group_by(Qualification.qual_id)
            if sort == "pass_rate":
                # 합격률 높은 순 / 낮은 순 (NULL은 항상 마지막)
                query = query.order_by(
                    desc(func.avg(QualificationStats.pass_rate)).nulls_last()
                    if sort_desc else
                    asc(func.avg(QualificationStats.pass_rate)).nulls_last()
                )
            else:
                # 난이도 정렬: 표시값은 pass_rate 역함수이므로 pass_rate 역순으로 정렬
                # (difficulty_score 컬럼은 로딩 시점 계산값이라 표시값과 불일치 → pass_rate 사용)
                query = query.order_by(
                    asc(func.avg(QualificationStats.pass_rate)).nulls_last()
                    if sort_desc else
                    desc(func.avg(QualificationStats.pass_rate)).nulls_last()
                )
        
        # Apply pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        return items, total
    
    @staticmethod
    def get_filter_options(db: Session) -> dict:
        """Get available filter options. 단일 쿼리로 4개 컬럼 값 수집 후 Python에서 distinct (라운드트립 1회)."""
        rows = db.query(
            Qualification.main_field,
            Qualification.ncs_large,
            Qualification.qual_type,
            Qualification.managing_body,
        ).filter(Qualification.is_active == True).all()
        main_fields = sorted({r.main_field for r in rows if r.main_field})
        ncs_large = sorted({r.ncs_large for r in rows if r.ncs_large})
        qual_types = sorted({r.qual_type for r in rows if r.qual_type})
        managing_bodies = sorted({r.managing_body for r in rows if r.managing_body})
        return {
            "main_fields": main_fields,
            "ncs_large": ncs_large,
            "qual_types": qual_types,
            "managing_bodies": managing_bodies,
        }
    
    @staticmethod
    def create(db: Session, obj_in: QualificationCreate) -> Qualification:
        """Create new qualification."""
        db_obj = Qualification(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def update(
        db: Session, 
        db_obj: Qualification, 
        obj_in: QualificationUpdate
    ) -> Qualification:
        """Update qualification."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def delete(db: Session, db_obj: Qualification) -> None:
        """Delete qualification."""
        db.delete(db_obj)
        db.commit()


# ============== QualificationStats CRUD ==============

class QualificationStatsCRUD:
    """CRUD operations for QualificationStats."""
    
    @staticmethod
    def get_by_id(db: Session, stat_id: int) -> Optional[QualificationStats]:
        """Get stats by ID."""
        # Stats usually fetched via qual_id in data loader
        return db.query(QualificationStats).filter(
            QualificationStats.stat_id == stat_id
        ).first()
    
    @staticmethod
    def get_by_qual_id(
        db: Session, 
        qual_id: int,
        year: Optional[int] = None
    ) -> List[QualificationStats]:
        """Get stats by qualification ID."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     stats = data_loader.get_stats_by_qual_id(qual_id)
        #     if year:
        #         stats = [s for s in stats if s.year == year]
        #     # sort desc
        #     stats.sort(key=lambda x: (x.year, x.exam_round), reverse=True)
        #     return stats
            
        query = db.query(QualificationStats).filter(
            QualificationStats.qual_id == qual_id
        )
        if year:
            query = query.filter(QualificationStats.year == year)
        return query.order_by(desc(QualificationStats.year), desc(QualificationStats.exam_round)).all()
    
    @staticmethod
    def get_latest_by_qual_id(
        db: Session, 
        qual_id: int
    ) -> Optional[QualificationStats]:
        """Get latest stats for a qualification."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     stats = data_loader.get_stats_by_qual_id(qual_id)
        #     if not stats: return None
        #     return max(stats, key=lambda s: (s.year, s.exam_round))

        return db.query(QualificationStats).filter(
            QualificationStats.qual_id == qual_id
        ).order_by(
            desc(QualificationStats.year), 
            desc(QualificationStats.exam_round)
        ).first()
    
    @staticmethod
    def create(db: Session, obj_in: QualificationStatsCreate) -> QualificationStats:
        """Create new stats entry."""
        db_obj = QualificationStats(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def upsert(
        db: Session, 
        qual_id: int,
        year: int,
        exam_round: int,
        **kwargs
    ) -> QualificationStats:
        """Upsert stats entry."""
        db_obj = db.query(QualificationStats).filter(
            and_(
                QualificationStats.qual_id == qual_id,
                QualificationStats.year == year,
                QualificationStats.exam_round == exam_round
            )
        ).first()
        
        if db_obj:
            for key, value in kwargs.items():
                setattr(db_obj, key, value)
        else:
            db_obj = QualificationStats(
                qual_id=qual_id,
                year=year,
                exam_round=exam_round,
                **kwargs
            )
            db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def update(
        db: Session,
        db_obj: QualificationStats,
        obj_in: QualificationStatsUpdate
    ) -> QualificationStats:
        """Update stats entry."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def delete(db: Session, db_obj: QualificationStats) -> None:
        """Delete stats entry."""
        db.delete(db_obj)
        db.commit()


# ============== MajorQualificationMap CRUD ==============

class MajorQualificationMapCRUD:
    """CRUD operations for MajorQualificationMap."""
    
    @staticmethod
    def get_by_major(
        db: Session, 
        major: str,
        limit: int = 50
    ) -> List[MajorQualificationMap]:
        """Get qualification mappings for a major."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_recommendations_by_major(major, limit)

        return db.query(MajorQualificationMap).options(
            joinedload(MajorQualificationMap.qualification)
        ).filter(
            MajorQualificationMap.major == major
        ).order_by(
            desc(MajorQualificationMap.score)
        ).limit(limit).all()
    
    @staticmethod
    def get_by_major_with_stats(
        db: Session,
        major: str,
        limit: int = 50
    ) -> List[MajorQualificationMap]:
        """Get qualification mappings with qualification stats."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     # data_loader returns mappings with qualifications linked (and stats linked to qual)
        #     return data_loader.get_recommendations_by_major(major, limit)
            
        return db.query(MajorQualificationMap).options(
            joinedload(MajorQualificationMap.qualification).joinedload(Qualification.stats)
        ).filter(
            MajorQualificationMap.major == major
        ).order_by(
            desc(MajorQualificationMap.score)
        ).limit(limit).all()
    
    @staticmethod
    def get_majors_list(db: Session) -> List[str]:
        """Get list of all majors from the dedicated Major table."""
        return [r[0] for r in db.query(Major.major_name).order_by(Major.major_name).all()]
    
    @staticmethod
    def create(db: Session, obj_in: MajorQualificationMapCreate) -> MajorQualificationMap:
        """Create new mapping."""
        db_obj = MajorQualificationMap(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def upsert(
        db: Session,
        major: str,
        qual_id: int,
        score: float = 1.0,
        weight: Optional[float] = None,
        reason: Optional[str] = None
    ) -> MajorQualificationMap:
        """Upsert mapping."""
        db_obj = db.query(MajorQualificationMap).filter(
            and_(
                MajorQualificationMap.major == major,
                MajorQualificationMap.qual_id == qual_id
            )
        ).first()
        
        if db_obj:
            db_obj.score = score
            if weight is not None:
                db_obj.weight = weight
            if reason is not None:
                db_obj.reason = reason
        else:
            db_obj = MajorQualificationMap(
                major=major,
                qual_id=qual_id,
                score=score,
                weight=weight,
                reason=reason
            )
            db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj


# ============== UserFavorite CRUD ==============

class UserFavoriteCRUD:
    """CRUD operations for UserFavorite."""
    
    @staticmethod
    def get_by_user(
        db: Session, 
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[UserFavorite], int]:
        """Get user's favorites."""
        query = db.query(UserFavorite).filter(UserFavorite.user_id == user_id)
        total = query.count()
        
        offset = (page - 1) * page_size
        items = query.options(
            joinedload(UserFavorite.qualification)
        ).order_by(
            desc(UserFavorite.created_at)
        ).offset(offset).limit(page_size).all()
        
        return items, total
    
    @staticmethod
    def get_by_user_and_qual(
        db: Session,
        user_id: str,
        qual_id: int
    ) -> Optional[UserFavorite]:
        """Get specific favorite."""
        return db.query(UserFavorite).filter(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.qual_id == qual_id
            )
        ).first()
    
    @staticmethod
    def is_favorite(db: Session, user_id: str, qual_id: int) -> bool:
        """Check if qualification is in user's favorites."""
        return db.query(UserFavorite).filter(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.qual_id == qual_id
            )
        ).first() is not None
    
    @staticmethod
    def add_favorite(db: Session, user_id: str, qual_id: int) -> UserFavorite:
        """Add to favorites."""
        existing = UserFavoriteCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if existing:
            return existing
        
        db_obj = UserFavorite(user_id=user_id, qual_id=qual_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def remove_favorite(db: Session, user_id: str, qual_id: int) -> bool:
        """Remove from favorites."""
        db_obj = UserFavoriteCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


# ============== User Acquired Certs CRUD ==============

class AcquiredCertCRUD:
    """CRUD for user acquired (earned) certifications."""

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: str,
        page: int = 1,
        page_size: int = 100
    ) -> tuple[List[UserAcquiredCert], int]:
        """Get user's acquired certs."""
        query = db.query(UserAcquiredCert).filter(UserAcquiredCert.user_id == user_id)
        total = query.count()
        offset = (page - 1) * page_size
        items = query.options(
            joinedload(UserAcquiredCert.qualification)
        ).order_by(desc(UserAcquiredCert.created_at)).offset(offset).limit(page_size).all()
        return items, total

    @staticmethod
    def count_by_user(db: Session, user_id: str) -> int:
        """Count acquired certs for user."""
        return db.query(UserAcquiredCert).filter(UserAcquiredCert.user_id == user_id).count()

    @staticmethod
    def get_by_user_and_qual(db: Session, user_id: str, qual_id: int) -> Optional[UserAcquiredCert]:
        """Get one acquired cert record."""
        return db.query(UserAcquiredCert).filter(
            and_(
                UserAcquiredCert.user_id == user_id,
                UserAcquiredCert.qual_id == qual_id
            )
        ).first()

    @staticmethod
    def add(db: Session, user_id: str, qual_id: int, acquired_at=None) -> UserAcquiredCert:
        """Add acquired cert."""
        existing = AcquiredCertCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if existing:
            return existing
        obj = UserAcquiredCert(user_id=user_id, qual_id=qual_id, acquired_at=acquired_at)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def remove(db: Session, user_id: str, qual_id: int) -> bool:
        """Remove acquired cert."""
        obj = AcquiredCertCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False


acquired_cert_crud = AcquiredCertCRUD()

# ============== Aggregated Stats ==============

def get_qualification_aggregated_stats(
    db: Session,
    qual_id: int
) -> dict:
    """Get aggregated stats for a qualification."""
    # from app.services.data_loader import data_loader
    
    # if data_loader.is_ready:
    #     stats = data_loader.get_stats_by_qual_id(qual_id)
    #     latest = max(stats, key=lambda s: (s.year, s.exam_round)) if stats else None
        
    #     if not latest:
    #         return {
    #             "latest_pass_rate": None,
    #             "avg_difficulty": None,
    #             "total_candidates": None,
    #         }
        
    #     # Calculate avg difficult
    #     valid_diff = [s.difficulty_score for s in stats if s.difficulty_score is not None]
    #     avg_difficulty = sum(valid_diff)/len(valid_diff) if valid_diff else None
        
    #     # Total candidates
    #     total_candidates = sum((s.candidate_cnt or 0) for s in stats)
        
    #     return {
    #         "latest_pass_rate": latest.pass_rate,
    #         "avg_difficulty": round(avg_difficulty, 2) if avg_difficulty is not None else None,
    #         "total_candidates": total_candidates,
    #     }

    # 1. Get raw stats from DB
    raw_stats = db.query(
        func.avg(QualificationStats.pass_rate).label("avg_pass_rate"),
        func.avg(QualificationStats.difficulty_score).label("avg_diff"),
        func.sum(QualificationStats.candidate_cnt).label("total_cands"),
        func.count(QualificationStats.stat_id).label("num_records")
    ).filter(QualificationStats.qual_id == qual_id).first()
    
    if not raw_stats or not raw_stats.num_records:
        return {
            "latest_pass_rate": None,
            "avg_difficulty": None,
            "total_candidates": None,
        }
    
    import math

    C_THRESHOLD = 5000.0
    K_THRESHOLD = 8.0
    PRIOR_DIFF   = 5.5

    GRADE_ADJ = {"기술사": 1.2, "기능장": 0.8, "기사": 0.4, "산업기사": 0.2, "기능사": -0.3}
    GRADE_MAX = {"기술사": 10.0, "기능장": 9.5, "기사": 9.0, "산업기사": 8.5, "기능사": 8.0}

    # 2. Base difficulty from pass rate
    avg_pass_rate = raw_stats.avg_pass_rate if raw_stats.avg_pass_rate is not None else 35.0
    base_diff = max(1.0, min(9.9, (100.0 - avg_pass_rate) / 10.0))

    total_cands = raw_stats.total_cands or 0
    num_records = raw_stats.num_records or 0

    # 3. Log-scale Bayesian smoothing (응시자 적으면 Prior로 강하게 수렴)
    conf_cands   = min(1.0, math.log1p(total_cands) / math.log1p(C_THRESHOLD))
    conf_records = min(1.0, num_records / K_THRESHOLD)
    confidence = conf_cands * 0.70 + conf_records * 0.30

    smoothed = base_diff * confidence + PRIOR_DIFF * (1.0 - confidence)

    # 4. Level-based additive adjustment (곱셈 → 덧셈, 상한 초과 방지)
    from app.models import Qualification
    qual = db.query(Qualification).filter(Qualification.qual_id == qual_id).first()

    grade_adj = 0.0
    max_cap   = 9.5
    if qual:
        if qual.qual_type == "국가기술자격":
            grade_adj = GRADE_ADJ.get(qual.grade_code, 0.0)
            max_cap   = GRADE_MAX.get(qual.grade_code, 9.0)
        elif qual.qual_type == "국가전문자격":
            grade_adj = 0.5
            max_cap   = 9.5
        elif qual.qual_type and "민간" in qual.qual_type:
            grade_adj = -0.5
            max_cap   = 8.5

    final_difficulty = smoothed + grade_adj * confidence
    final_difficulty = max(1.0, min(max_cap, final_difficulty))

    # 5. Get latest pass rate safely
    latest = QualificationStatsCRUD.get_latest_by_qual_id(db, qual_id)
    latest_pass_rate = latest.pass_rate if latest else None
    
    return {
        "latest_pass_rate": latest_pass_rate,
        "avg_difficulty": round(final_difficulty, 1),
        "total_candidates": int(total_cands or 0),
    }


def get_qualification_aggregated_stats_bulk(db: Session, qual_ids: List[int]) -> dict:
    """Get aggregated stats for multiple qualifications in bulk. = ANY(:ids)로 바인드 1개만 사용해 로그 폭주 방지."""
    if not qual_ids:
        return {}

    stats_map = {}
    latest_pass_rate_map = {}
    qual_metadata = {}

    # 1. Raw aggregated stats (바인드 1개: ids)
    rows1 = db.execute(text("""
        SELECT qual_id,
               AVG(pass_rate) AS avg_pass_rate,
               AVG(difficulty_score) AS avg_diff,
               COALESCE(SUM(candidate_cnt), 0) AS total_cands,
               COUNT(stat_id) AS num_records
        FROM qualification_stats
        WHERE qual_id = ANY(:ids)
        GROUP BY qual_id
    """), {"ids": qual_ids}).fetchall()
    for r in rows1:
        stats_map[r.qual_id] = SimpleNamespace(
            qual_id=r.qual_id,
            avg_pass_rate=float(r.avg_pass_rate) if r.avg_pass_rate is not None else None,
            avg_diff=float(r.avg_diff) if r.avg_diff is not None else None,
            total_cands=r.total_cands or 0,
            num_records=r.num_records or 0,
        )

    # 2. Latest pass rate per qual_id (DISTINCT ON)
    rows2 = db.execute(text("""
        SELECT DISTINCT ON (qual_id) qual_id, pass_rate
        FROM qualification_stats
        WHERE qual_id = ANY(:ids)
        ORDER BY qual_id, year DESC, exam_round DESC
    """), {"ids": qual_ids}).fetchall()
    for r in rows2:
        latest_pass_rate_map[r.qual_id] = float(r.pass_rate) if r.pass_rate is not None else None

    # 3. Qualification metadata for level weighting
    rows3 = db.execute(text("""
        SELECT qual_id, qual_type, grade_code
        FROM qualification
        WHERE qual_id = ANY(:ids)
    """), {"ids": qual_ids}).fetchall()
    for r in rows3:
        qual_metadata[r.qual_id] = SimpleNamespace(qual_type=r.qual_type, grade_code=r.grade_code)

    # 4. Process all results
    import math

    # 응시자 수가 적을수록 Prior로 강하게 당김 (로그 스케일 Bayesian smoothing)
    # 기준: 5000명 이상이면 데이터 신뢰도 100%, 8회 이상이면 회차 신뢰도 100%
    C_THRESHOLD = 5000.0
    K_THRESHOLD = 8.0
    PRIOR_DIFF   = 5.5   # 중립 Prior (이전 6.5에서 하향 - 10 쏠림 방지)

    # 자격 등급별 가산/감산 조정값 (곱셈→덧셈으로 전환: 상한 초과 방지)
    GRADE_ADJ = {
        "기술사": 1.2,
        "기능장": 0.8,
        "기사":   0.4,
        "산업기사": 0.2,
        "기능사": -0.3,
    }
    # 등급별 최대 허용 난이도 상한 (10 쏠림 방지)
    GRADE_MAX = {
        "기술사": 10.0,
        "기능장": 9.5,
        "기사":   9.0,
        "산업기사": 8.5,
        "기능사":   8.0,
    }

    results = {}

    for q_id in qual_ids:
        raw = stats_map.get(q_id)
        if not raw or not raw.num_records:
            results[q_id] = {
                "latest_pass_rate": None,
                "avg_difficulty": None,
                "total_candidates": 0,
            }
            continue

        avg_pass_rate = raw.avg_pass_rate if raw.avg_pass_rate is not None else 35.0
        total_cands   = raw.total_cands or 0
        num_records   = raw.num_records or 0

        # 1) 합격률 → 원시 난이도 (0~100% → 1.0~10.0)
        base_diff = max(1.0, min(9.9, (100.0 - avg_pass_rate) / 10.0))

        # 2) 로그 스케일 응시자 신뢰도: 응시자 적을수록 Prior로 훨씬 강하게 당김
        conf_cands   = min(1.0, math.log1p(total_cands) / math.log1p(C_THRESHOLD))
        conf_records = min(1.0, num_records / K_THRESHOLD)
        # 응시자 수 가중치 70%, 회차 수 가중치 30%
        confidence = conf_cands * 0.70 + conf_records * 0.30

        # 3) Bayesian 스무딩 (데이터 희소 → Prior 쪽으로 수렴)
        smoothed = base_diff * confidence + PRIOR_DIFF * (1.0 - confidence)

        # 4) 자격 등급별 가산점 (confidence 비례 적용: 불확실하면 조정도 작게)
        qual = qual_metadata.get(q_id)
        grade_adj = 0.0
        max_cap   = 9.5
        if qual:
            if qual.qual_type == "국가기술자격":
                grade_adj = GRADE_ADJ.get(qual.grade_code, 0.0)
                max_cap   = GRADE_MAX.get(qual.grade_code, 9.0)
            elif qual.qual_type == "국가전문자격":
                grade_adj = 0.5
                max_cap   = 9.5
            elif qual.qual_type and "민간" in qual.qual_type:
                grade_adj = -0.5
                max_cap   = 8.5

        final_difficulty = smoothed + grade_adj * confidence
        final_difficulty = max(1.0, min(max_cap, final_difficulty))

        results[q_id] = {
            "latest_pass_rate": latest_pass_rate_map.get(q_id),
            "avg_difficulty": round(final_difficulty, 1),
            "total_candidates": int(total_cands),
        }

    return results


# ============== Job CRUD ==============

class JobCRUD:
    """CRUD operations for Job."""
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Job], int]:
        """Get list of jobs."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     items = data_loader.get_jobs_list(q)
        #     return items, len(items)
            
        query = db.query(Job)
        if q:
            query = query.filter(
                or_(
                    Job.job_name.ilike(f"%{q}%"),
                    Job.outlook_summary.ilike(f"%{q}%")
                )
            )
        total = query.count()
        
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    @staticmethod
    def get_by_id(db: Session, job_id: int) -> Optional[Job]:
        """Get job by ID with related qualifications."""
        # Always use DB for detailed view to show enriched mappings
        return db.query(Job).options(
            joinedload(Job.qualifications)
        ).filter(Job.job_id == job_id).first()


# ============== Major CRUD ==============

class MajorCRUD:
    """CRUD operations for Major."""
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Major], int]:
        """Get list of majors."""
        query = db.query(Major)
        if q:
            query = query.filter(Major.major_name.ilike(f"%{q}%"))
        
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        return items, total


# ============== Export CRUD instances ==============

qualification_crud = QualificationCRUD()
stats_crud = QualificationStatsCRUD()
major_map_crud = MajorQualificationMapCRUD()
favorite_crud = UserFavoriteCRUD()
job_crud = JobCRUD()
major_crud = MajorCRUD()
