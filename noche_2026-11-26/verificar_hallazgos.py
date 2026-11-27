#!/usr/bin/env python3
"""Re-lectura independiente (directo a SQL, no desde las fotos) de los hallazgos clave. SOLO LECTURA."""
from lib_lectura import conn, q
CHEQUEOS = [
 ("felix", "SELECT idproducto, descripcion FROM productos WHERE idproducto IN ('01007','01055','01038')"),
 ("hacienda_del_rio", "SELECT idproducto, descripcion FROM productos WHERE idproducto IN ('01007','01055','01038')"),
 ("villas_del_rey", "SELECT p.idproducto, p.descripcion, d.precio FROM productos p JOIN productosdetalle d ON d.idproducto=p.idproducto WHERE p.idproducto='01114'"),
 ("montejano", "SELECT p.idproducto, p.descripcion, d.precio FROM productos p JOIN productosdetalle d ON d.idproducto=p.idproducto WHERE p.idproducto='01114'"),
 ("cine_curto", "SELECT idinsumo, descripcion, unidad FROM insumos WHERE idinsumo IN ('001034','005001','001036')"),
 ("felix", "SELECT idinsumo, descripcion, unidad FROM insumos WHERE idinsumo IN ('001034','005001','001036')"),
 ("felix", "SELECT p.idinsumospresentaciones, p.descripcion, p.rendimiento, d.costo FROM insumospresentaciones p JOIN insumospresentacionesdetalle d ON d.idinsumospresentaciones=p.idinsumospresentaciones WHERE p.idinsumospresentaciones='001001'"),
 ("san_marcos", "SELECT p.idinsumospresentaciones, p.descripcion, p.rendimiento, d.costo FROM insumospresentaciones p JOIN insumospresentacionesdetalle d ON d.idinsumospresentaciones=p.idinsumospresentaciones WHERE p.idinsumospresentaciones='001001'"),
 ("felix", "SELECT TOP 5 CONVERT(varchar(10),fecha,120) dia, COUNT(*) n FROM cheques GROUP BY CONVERT(varchar(10),fecha,120) ORDER BY 1 DESC"),
 ("felix", "SELECT COUNT(*) traspasos FROM movsinv WHERE traspaso IS NOT NULL AND traspaso<>''"),
 ("montejano", "SELECT COUNT(*) insumos_costo_cero FROM insumosdetalle WHERE ISNULL(costo,0)=0"),
 ("felix", "SELECT COUNT(*) insumos_costo_cero FROM insumosdetalle WHERE ISNULL(costo,0)=0"),
 ("cine_curto", "SELECT idformadepago, descripcion, idformapago_SAT FROM formasdepago WHERE visible=1"),
 ("montejano", "SELECT usuario, nombre, administrador FROM usuarios WHERE usuario='MONTECARLO'"),
]
for cf, sql in CHEQUEOS:
    try:
        cn = conn(cf); cur = cn.cursor(); r = q(cur, sql); cn.close()
        print(f"[{cf}] {sql[:70]}...\n   -> {r}")
    except Exception as e: print(f"[{cf}] ERROR {e}")
