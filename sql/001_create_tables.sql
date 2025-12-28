CREATE TABLE IF NOT EXISTS inventory_skincare (
  id_produk SERIAL PRIMARY KEY,
  nama_produk TEXT NOT NULL,
  kategori TEXT NOT NULL,
  tanggal_beli DATE,
  tanggal_buka DATE,
  pao_bulan INT,
  tanggal_kadaluwarsa DATE,
  catatan TEXT
);

CREATE TABLE IF NOT EXISTS daily_analysis (
  id SERIAL PRIMARY KEY,
  tanggal DATE NOT NULL,
  uvi NUMERIC,
  humidity NUMERIC,
  temp_c NUMERIC,
  weather_main TEXT,
  rekomendasi TEXT
);