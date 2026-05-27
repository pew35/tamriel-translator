from sqlalchemy import Column, Integer, String, Text, UniqueConstraint

from database import Base


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id = Column(Integer, primary_key=True, index=True)

    eso_id = Column(String(50), nullable=False)
    unknown = Column(String(50), nullable=False)
    lang_index = Column(String(50), nullable=False)

    zh = Column(Text, nullable=False)
    en = Column(Text, nullable=False)

    category = Column(String(50), default="eso_term")

    __table_args__ = (
        UniqueConstraint("eso_id", "unknown", "lang_index", name="unique_eso_term"),
    )