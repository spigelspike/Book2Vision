from sqlmodel import Session, select
from src.database import engine, Book

def list_books():
    with Session(engine) as session:
        books = session.exec(select(Book)).all()
        print(f"Found {len(books)} books:")
        for book in books:
            print(f"ID: {book.id} | Title: {book.title} | Filename: {book.filename}")

if __name__ == "__main__":
    list_books()
