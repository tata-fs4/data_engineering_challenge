-- From the two most commonly appearing regions, which is the latest datasource?
WITH region_counts AS (
    SELECT region, COUNT(*) AS trip_count
    FROM trips
    GROUP BY region
    ORDER BY trip_count DESC
    LIMIT 2
), ranked_datasources AS (
    SELECT t.region,
           t.datasource,
           t.started_at,
           ROW_NUMBER() OVER (PARTITION BY t.region ORDER BY t.started_at DESC) AS rn
    FROM trips t
    INNER JOIN region_counts rc ON rc.region = t.region
)
SELECT region, datasource, started_at
FROM ranked_datasources
WHERE rn = 1;

-- What regions has the "cheap_mobile" datasource appeared in?
SELECT DISTINCT region
FROM trips
WHERE datasource = 'cheap_mobile'
ORDER BY region;
