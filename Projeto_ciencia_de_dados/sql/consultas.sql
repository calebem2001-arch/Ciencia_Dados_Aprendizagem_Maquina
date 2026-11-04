-- Dialeto: SQLite 3. Tabelas carregadas por scripts/analise.py em memória.
-- Dados simulados. O banco MySQL do TCC não é alterado.

-- CONSULTA 01_atendimentos_mensais
SELECT mes, COUNT(*) AS acoes, SUM(atendimentos) AS atendimentos,
       SUM(voluntarios_presentes) AS presencas_voluntarios
FROM acoes GROUP BY mes ORDER BY mes;

-- CONSULTA 02_doacoes_por_item
SELECT i.nome, i.unidade, ROUND(SUM(d.quantidade), 2) AS total_doado
FROM doacoes d JOIN itens i ON i.item_id = d.item_id
GROUP BY i.item_id, i.nome, i.unidade ORDER BY i.nome;

-- CONSULTA 03_frequencia_falta
SELECT nome, unidade, COUNT(*) AS meses,
       SUM(houve_falta) AS meses_com_falta,
       ROUND(100.0*AVG(houve_falta), 2) AS percentual_meses_com_falta
FROM item_mes GROUP BY item_id, nome, unidade
ORDER BY percentual_meses_com_falta DESC;

-- CONSULTA 04_cobertura_por_item
SELECT nome, unidade, ROUND(SUM(doado), 2) AS recebido,
       ROUND(SUM(demanda), 2) AS solicitado,
       ROUND(100.0*SUM(consumido)/NULLIF(SUM(demanda), 0), 2) AS percentual_demanda_atendida
FROM item_mes GROUP BY item_id, nome, unidade ORDER BY nome;

-- CONSULTA 05_estoque_ultimo_mes
SELECT nome, unidade, estoque_final, estoque_minimo,
       CASE WHEN estoque_final < estoque_minimo THEN 'REPOR' ELSE 'OK' END AS situacao
FROM item_mes WHERE mes = (SELECT MAX(mes) FROM item_mes) ORDER BY nome;

-- CONSULTA 06_balanco_estoque
SELECT COUNT(*) AS linhas,
       SUM(CASE WHEN ABS(estoque_inicial + doado - consumido - estoque_final) > 0.011
                THEN 1 ELSE 0 END) AS erros_balanco,
       SUM(CASE WHEN ABS(demanda - consumido - demanda_nao_atendida) > 0.011
                THEN 1 ELSE 0 END) AS erros_demanda,
       SUM(CASE WHEN estoque_final < 0 THEN 1 ELSE 0 END) AS estoques_negativos
FROM item_mes;

-- CONSULTA 07_dispersao_arroz
SELECT mes, atendimentos, demanda AS demanda_arroz_kg,
       doado AS doacao_arroz_kg, consumido AS consumo_arroz_kg
FROM item_mes WHERE item_id = 'I01' ORDER BY mes;

-- CONSULTA 08_integridade_doacoes
SELECT COUNT(*) AS doacoes_validas,
       COUNT(*) - COUNT(DISTINCT d.doacao_id) AS ids_duplicados,
       SUM(CASE WHEN i.item_id IS NULL THEN 1 ELSE 0 END) AS itens_inexistentes,
       SUM(CASE WHEN d.quantidade IS NULL OR d.quantidade <= 0 THEN 1 ELSE 0 END) AS quantidades_invalidas
FROM doacoes d LEFT JOIN itens i ON i.item_id = d.item_id;
