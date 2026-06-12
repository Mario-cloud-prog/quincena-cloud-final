-- schema.sql
-- Esquema inicial de la base de datos MySQL para el proyecto Quincena.
-- Este archivo crea la base de datos y las tablas principales usadas por la API.
-- El backend FastAPI usa estas tablas para registrar gastos y construir el dashboard.

CREATE DATABASE IF NOT EXISTS quincena;
USE quincena;

-- Tabla de usuarios.
-- Guarda información básica del usuario y su presupuesto mensual esperado.
-- presupuesto_mensual se usa como referencia para calcular safe_to_spend.
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    ingreso_mensual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    presupuesto_mensual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de gastos.
-- Es la tabla principal del proyecto.
-- Cada registro representa un gasto hecho por un usuario en una fecha y categoría.
-- Esta tabla también alimentará al worker y a BigQuery ML.
CREATE TABLE IF NOT EXISTS gastos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabla de pronósticos.
-- Guarda resultados calculados por el sistema, como gasto proyectado y safe_to_spend.
-- En la versión integrada, estos valores podrán venir del worker y de BigQuery ML.
CREATE TABLE IF NOT EXISTS pronosticos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    mes VARCHAR(7) NOT NULL,
    proyectado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    normal_mensual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    safe_to_spend DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    mensaje VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Usuario de prueba para que la API pueda responder desde el primer día.
-- El Integrante 4 podrá agregar más datos ficticios en seed/seed_data.sql.
INSERT INTO usuarios (nombre, ingreso_mensual, presupuesto_mensual)
VALUES ('Usuario Demo', 12000.00, 6900.00);
