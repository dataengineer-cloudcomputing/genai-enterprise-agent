import sqlite3
import os

def create_database():
    # Définition du chemin de la base de données
    db_dir = "data"
    db_path = os.path.join(db_dir, "ev_market.db")
    
    # Assurer que le dossier data existe
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[SQL] Création du dossier : {db_dir}")

    print(f"[SQL] Connexion à la base de données : {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Nettoyage de l'ancienne table pour éviter les doublons ou conflits de schéma
    print("[SQL] Réinitialisation de la table Ventes...")
    cursor.execute("DROP TABLE IF EXISTS Ventes;")

    # Création de la table avec un schéma strict et des types appropriés
    cursor.execute('''
        CREATE TABLE Ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            marque TEXT NOT NULL,
            modele TEXT NOT NULL,
            pays TEXT NOT NULL,
            unites_vendues INTEGER NOT NULL,
            prix_moyen_vente REAL NOT NULL,
            chiffre_affaires REAL NOT NULL
        );
    ''')
    print("[SQL] Table Ventes créée avec succès.")

    # Jeu de données d'entreprise enrichi (Tesla, BYD, BMW) pour l'année 2025
    donnees_ventes = [
        # Données Tesla
        ('2025-01-15', 'Tesla', 'Model Y', 'Allemagne', 2000, 45000.0, 90000000.0),
        ('2025-02-20', 'Tesla', 'Model 3', 'Allemagne', 500, 50000.0, 25000000.0),
        
        # Données BYD
        ('2025-03-10', 'BYD', 'Atto 3', 'France', 1200, 38000.0, 45600000.0),
        ('2025-05-18', 'BYD', 'Seal', 'Allemagne', 600, 42000.0, 25200000.0),
        
        # Données BMW (Nouveaux enregistrements pour valider ton test de Phase 3)
        ('2025-06-12', 'BMW', 'i4', 'Allemagne', 1500, 55000.0, 82500000.0),
        ('2025-08-22', 'BMW', 'iX3', 'Allemagne', 800, 65000.0, 52000000.0)
    ]

    # Insertion en masse (Bulk Insert) sécurisée pour éviter les injections SQL
    cursor.executemany('''
        INSERT INTO Ventes (date, marque, modele, pays, unites_vendues, prix_moyen_vente, chiffre_affaires)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    ''', donnees_ventes)

    # Validation des écritures dans le fichier .db
    conn.commit()
    
    # Petite vérification de contrôle pour afficher le nombre de lignes insérées
    cursor.execute("SELECT COUNT(*) FROM Ventes;")
    total_lignes = cursor.fetchone()[0]
    
    print(f"[SUCCESS] Base de données initialisée. {total_lignes} transactions enregistrées.")
    
    # Fermeture propre de la connexion
    conn.close()

if __name__ == "__main__":
    create_database()