-- Script de migración para agregar campos específicos de "Bono de Servicios Ambientales"
-- Ejecutar en PostgreSQL

-- Agregar nuevos campos a la tabla proyecto
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS de_quien_compro VARCHAR(255);
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS hectareas_bono NUMERIC(10, 2);
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS anio_bono INTEGER;
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS tipo_asociacion VARCHAR(100); -- ALPROEA o APROSEC
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS fecha_emision_bono DATE;
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS fecha_vencimiento_bono DATE;
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS pago_total_bono NUMERIC(12, 2);
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS hectareas_finanzas NUMERIC(10, 2);
ALTER TABLE proyecto ADD COLUMN IF NOT EXISTS precio_por_hectarea NUMERIC(12, 2); -- Campo calculado

-- Comentarios para documentar los campos
COMMENT ON COLUMN proyecto.de_quien_compro IS 'Campo específico para Bono de Servicios Ambientales - De quién compró';
COMMENT ON COLUMN proyecto.hectareas_bono IS 'Hectáreas para Bono de Servicios Ambientales';
COMMENT ON COLUMN proyecto.anio_bono IS 'Año para Bono de Servicios Ambientales';
COMMENT ON COLUMN proyecto.tipo_asociacion IS 'ALPROEA E.A.S o APROSEC - Toggle selection';
COMMENT ON COLUMN proyecto.fecha_emision_bono IS 'Fecha de emisión del bono (opcional)';
COMMENT ON COLUMN proyecto.fecha_vencimiento_bono IS 'Fecha de vencimiento del bono (opcional)';
COMMENT ON COLUMN proyecto.pago_total_bono IS 'Pago total para cálculo de precio por hectárea';
COMMENT ON COLUMN proyecto.hectareas_finanzas IS 'Hectáreas para cálculo financiero';
COMMENT ON COLUMN proyecto.precio_por_hectarea IS 'Precio calculado por hectárea (pago_total_bono / hectareas_finanzas)';

-- Crear índices para mejorar performance en consultas
CREATE INDEX IF NOT EXISTS idx_proyecto_tipo_asociacion ON proyecto(tipo_asociacion);
CREATE INDEX IF NOT EXISTS idx_proyecto_anio_bono ON proyecto(anio_bono);
CREATE INDEX IF NOT EXISTS idx_proyecto_fecha_emision_bono ON proyecto(fecha_emision_bono);
CREATE INDEX IF NOT EXISTS idx_proyecto_fecha_vencimiento_bono ON proyecto(fecha_vencimiento_bono);

-- Verificar que los campos se agregaron correctamente
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'proyecto' 
AND column_name IN (
    'de_quien_compro', 
    'hectareas_bono', 
    'anio_bono', 
    'tipo_asociacion',
    'fecha_emision_bono',
    'fecha_vencimiento_bono',
    'pago_total_bono',
    'hectareas_finanzas',
    'precio_por_hectarea'
);
