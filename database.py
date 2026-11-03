from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///prices.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    target_price = Column(Float)
    
    listings = relationship("ProductListing", back_populates="product", cascade="all, delete-orphan")

class ProductListing(Base):
    __tablename__ = "product_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    store_name = Column(String)
    url = Column(String)
    
    product = relationship("Product", back_populates="listings")
    history = relationship("PriceHistory", back_populates="listing", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("product_listings.id"))
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    listing = relationship("ProductListing", back_populates="history")

def init_db():
    Base.metadata.create_all(bind=engine)