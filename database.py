from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

engine = create_engine("sqlite:///prices.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    target_price = Column(Float, nullable=False)
    
    # Un produs are mai multe linkuri (oferte) pe diverse site-uri
    listings = relationship("ProductListing", back_populates="product", cascade="all, delete-orphan")

class ProductListing(Base):
    __tablename__ = "product_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_name = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    
    product = relationship("Product", back_populates="listings")
    history = relationship("PriceHistory", back_populates="listing", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("product_listings.id"), nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    listing = relationship("ProductListing", back_populates="history")

def init_db():
    Base.metadata.create_all(bind=engine)