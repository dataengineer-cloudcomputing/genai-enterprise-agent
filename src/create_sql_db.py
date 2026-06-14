import sqlite3
import os

def create_database():
    db_dir = "data"
    db_path = os.path.join(db_dir, "ev_market.db")
    
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[SQL] Création du dossier : {db_dir}")

    print(f"[SQL] Connexion à la base de données : {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("[SQL] Réinitialisation de la table Ventes...")
    cursor.execute("DROP TABLE IF EXISTS Ventes;")

    # Schéma relationnel strict — Alignement avec les colonnes attendues par l'agent
    cursor.execute('''
        CREATE TABLE Ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            annee INTEGER NOT NULL,
            marque TEXT NOT NULL,
            modele TEXT NOT NULL,
            pays TEXT NOT NULL,
            unites_vendues INTEGER NOT NULL,
            chiffre_affaires REAL NOT NULL
        );
    ''')
    print("[SQL] Table Ventes créée avec succès.")

    # Ingestion du jeu de données représentatif de l'exercice fiscal 2025
    donnees_ventes = [
        ('2025-09-30', 2025, 'Audi', 'Q8 e-tron', 'Europe', 24000, 97400000.0),
        ('2025-09-30', 2025, 'BMW', 'i4 / iX3', 'Allemagne', 2300, 134500000.0),
        ('2025-09-30', 2025, 'BYD', 'Atto 3 / Seal', 'Europe', 1800, 70800000.0),
        ('2025-09-30', 2025, 'Hyundai', 'IONIQ 5', 'Europe', 22000, 39200000.0),
        ('2025-09-30', 2025, 'Hyundai', 'IONIQ 6', 'Europe', 19000, 35000000.0),
        ('2025-09-30', 2025, 'Mercedes', 'EQS', 'Europe', 18000, 134500000.0),
        ('2025-09-30', 2025, 'Renault', 'Renault 5 EV', 'Europe', 38000, 38300000.0),
        ('2025-09-30', 2025, 'Megane E-Tech', 'Europe', 22000, 24000000.0),
        ('2025-09-30', 2025, 'Rivian', 'R1T / R1S', 'Europe', 8500, 38900000.0),
        ('2025-09-30', 2025, 'Stellantis', 'Peugeot e-208', 'Europe', 52000, 72000000.0),
        ('2025-09-30', 2025, 'Stellantis', 'Fiat 500e', 'Europe', 31000, 46700000.0),
        ('2025-09-30', 2025, 'Tesla', 'Model Y', 'Allemagne', 43000, 115000000.0),
        ('2025-09-30', 2025, 'Volkswagen', 'ID.4', 'Europe', 45000, 55000000.0),
        ('2025-09-30', 2025, 'Volkswagen', 'ID.7', 'Europe', 28000, 34500000.0)
    ]

    cursor.executemany('''
        INSERT INTO Ventes (date, annee, marque, modele, pays, unites_vendues, chiffre_affaires)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    ''', donnees_ventes)

    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM Ventes;")
    total_lignes = cursor.fetchone()[0]
    print(f"[SUCCESS] Base SQL enrichie. {total_lignes} lignes enregistrées.")
    
    conn.close()

if __name__ == "__main__":
    create_database()