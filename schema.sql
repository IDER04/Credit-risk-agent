-- Credit Risk Agent: schema and SYNTHETIC sample data.
-- All names, amounts and dates below are fictional.
-- Usage: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS RisqueClt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE RisqueClt;

DROP TABLE IF EXISTS IncidentPaiement;
DROP TABLE IF EXISTS Credit;
DROP TABLE IF EXISTS Client;

CREATE TABLE Client (
    IdClt             INT PRIMARY KEY,
    Nom               VARCHAR(100) NOT NULL,
    Ville             VARCHAR(100),
    DateNaiss         DATE,
    DateEmbauche      DATE,
    DateOuvertureCmpt DATE
);

CREATE TABLE Credit (
    IdCrdt      INT PRIMARY KEY,
    IdClt       INT NOT NULL,
    DateDemande DATE,
    TypeCredit  VARCHAR(50) NOT NULL,          -- Immobilier, Consommation, Auto...
    Montant     DECIMAL(12,2) NOT NULL,
    DureeMois   INT NOT NULL,
    Taux        DECIMAL(5,2) NOT NULL,         -- annual rate in %
    StatutCrdt  ENUM('accordé','refusé','en cours','soldé') DEFAULT 'accordé',
    FOREIGN KEY (IdClt) REFERENCES Client(IdClt)
);

CREATE TABLE IncidentPaiement (
    IdIncident      INT PRIMARY KEY,
    IdCrdt          INT NOT NULL,
    DateIncident    DATE,
    MontantIncident DECIMAL(12,2),
    TypeIncident    ENUM('retard','impayé','rejet de prélèvement') NOT NULL,
    FOREIGN KEY (IdCrdt) REFERENCES Credit(IdCrdt)
);

INSERT INTO Client VALUES
(101, 'Amine Benali',   'Casablanca', '1985-04-12', '2010-09-01', '2012-03-15'),
(102, 'Salma Curie',    'Agadir',     '1990-11-30', '2015-06-01', '2016-01-20'),
(103, 'Youssef Idrissi','Rabat',      '1978-02-08', '2005-01-10', '2008-07-02'),
(104, 'Nadia Fassi',    'Marrakech',  '1982-07-19', '2012-10-01', '2013-05-11'),
(105, 'Karim Alaoui',   'Tanger',     '1995-12-03', '2019-02-01', '2019-09-30'),
(106, 'Imane Tazi',     'Fès',        '1988-05-25', '2014-04-01', '2015-11-08'),
(107, 'Omar Chraibi',   'Agadir',     '1992-09-14', '2017-03-01', '2018-02-14'),
(108, 'Leila Berrada',  'Casablanca', '1999-01-22', '2022-09-01', '2023-01-05');

INSERT INTO Credit VALUES
(1001, 101, '2023-01-15', 'Immobilier',   150000.00, 240, 3.20, 'accordé'),
(1002, 102, '2023-02-20', 'Consommation',  10000.00,  48, 5.50, 'accordé'),
(1003, 103, '2023-03-10', 'Auto',          25000.00,  60, 4.80, 'refusé'),
(1004, 104, '2022-06-05', 'Consommation',  15000.00,  36, 6.00, 'accordé'),
(1005, 104, '2023-04-18', 'Auto',          30000.00,  60, 5.00, 'accordé'),
(1006, 105, '2023-05-22', 'Consommation',   8000.00,  24, 6.20, 'accordé'),
(1007, 106, '2021-09-12', 'Immobilier',   200000.00, 300, 3.50, 'accordé'),
(1008, 107, '2023-07-01', 'Auto',          18000.00,  48, 4.90, 'accordé');

INSERT INTO IncidentPaiement VALUES
(1, 1002, '2023-06-05', 450.00, 'retard'),
(2, 1002, '2023-07-05', 450.00, 'retard'),
(3, 1002, '2023-09-05', 450.00, 'impayé'),
(4, 1004, '2022-10-05', 480.00, 'retard'),
(5, 1004, '2022-11-05', 480.00, 'retard'),
(6, 1004, '2023-01-05', 480.00, 'impayé'),
(7, 1005, '2023-08-10', 600.00, 'rejet de prélèvement'),
(8, 1005, '2023-09-10', 600.00, 'impayé'),
(9, 1005, '2023-10-10', 600.00, 'impayé'),
(10, 1006, '2023-09-15', 350.00, 'retard');
