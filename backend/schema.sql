CREATE DATABASE IF NOT EXISTS quincena;
USE quincena;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    ingreso_mensual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    presupuesto_mensual DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gastos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

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

INSERT INTO usuarios (nombre, ingreso_mensual, presupuesto_mensual)
VALUES ('Usuario Demo', 12000.00, 6900.00);
