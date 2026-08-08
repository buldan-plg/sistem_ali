def test_koneksi(db):
    try:
        with db.cursor() as query:
            query.execute("""SELECT 1""")
        db.close()
        
        return True
    except Exception as e:
        print("DB error: ". e)
        return False