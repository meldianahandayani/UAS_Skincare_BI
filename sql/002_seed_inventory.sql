INSERT INTO inventory_skincare
(nama_brand, nama_produk, kategori, tanggal_beli, tanggal_buka, pao_bulan, tanggal_kedaluwarsa, volume_ml, harga_idr, catatan)
VALUES
-- ===== Sunscreen =====
('Azarine','Hydrasoothe Sunscreen Gel SPF45','Sunscreen','2025-10-25','2025-11-10',12,'2027-02-01',50,65000,'Dipakai pagi'),
('Emina','Sun Battle SPF50 PA++++','Sunscreen','2025-11-10','2025-11-12',12,'2027-04-01',50,35000,'Untuk reapply'),
('Biore','UV Aqua Rich Watery Essence','Sunscreen','2025-07-12','2025-07-13',12,'2026-12-01',50,150000,''),
('Hanasui','Collagen Water Sunscreen','Sunscreen','2025-12-01','2025-12-02',12,'2027-06-01',50,45000,''),
('Labore','Sunscreen (Labore Sunscreen)','Sunscreen','2025-12-02','2025-12-02',12,'2027-05-01',50,95000,'Sunscreen harian'),

-- ===== Cleanser =====
('COSRX','Low pH Good Morning Gel Cleanser','Cleanser','2025-08-15','2025-09-05',12,'2027-01-15',150,120000,''),
('Wardah','Lightening Micellar Water','Cleanser','2025-10-02','2025-10-03',6,'2026-09-01',100,28000,'Double cleanse'),
('Bioderma','Sensibio H2O','Cleanser','2025-06-10','2025-06-15',12,'2027-06-01',250,260000,''),
('Nivea','MicellAIR Skin Breathe','Cleanser','2025-09-01','2025-09-01',6,'2026-09-01',200,45000,''),
('Safi','White Expert Oil Control Cleanser','Cleanser','2025-10-01','2025-10-01',12,'2027-01-01',100,42000,''),
('Senka','Perfect Whip','Cleanser','2025-09-05','2025-09-05',12,'2027-01-01',120,78000,''),
('Cetaphil','Gentle Skin Cleanser','Cleanser','2025-09-15','2025-09-16',12,'2027-02-01',250,190000,''),

-- ===== Toner / Essence =====
('Hada Labo','Gokujyun Ultimate Moisturizing Lotion','Toner','2025-09-10','2025-10-01',12,'2026-12-01',100,52000,''),
('Pyunkang Yul','Essence Toner','Essence','2025-08-12','2025-08-15',12,'2027-01-01',100,170000,''),
('Some By Mi','AHA BHA PHA 30 Days Miracle Toner','Exfoliant','2025-08-20','2025-09-10',12,'2027-02-01',150,140000,''),
('Avoskin','Miraculous Refining Toner','Toner','2025-10-18','2025-11-01',12,'2027-01-01',100,125000,'Exfoliating toner (cek toleransi kulit)'),

-- ===== Serum / Ampoule =====
('Somethinc','Niacinamide + Moisture Sabi Beta Glucan Serum','Serum','2025-11-20','2025-12-01',12,'2027-01-01',20,115000,''),
('Garnier','Bright Complete Vitamin C Serum','Serum','2025-10-15','2025-10-16',6,'2026-10-01',30,95000,'Pagi (kadang)'),
('Skintific','Niacinamide Brightening Serum','Serum','2025-12-05','2025-12-06',12,'2027-05-01',20,145000,''),
('SKIN1004','Brightening (Tone Brightening Ampoule/Capsule Ampoule)','Serum','2025-12-05','2025-12-10',12,'2027-06-01',30,165000,'Brightening serum/ampoule'),

-- ===== Retinoid =====
('The Ordinary','Retinol 0.2% in Squalane','Retinoid','2025-09-25','2025-10-20',6,'2026-11-01',30,210000,'Malam tertentu'),
('Olay','Regenerist Retinol24 Night Moisturizer','Retinoid','2025-10-05','2025-10-10',12,'2027-01-01',50,390000,''),
('Avoskin','Retinol (Avoskin Retinol Serum)','Retinoid','2025-11-28','2025-12-03',6,'2026-12-01',30,170000,'Dipakai malam tertentu'),

-- ===== Exfoliant (non-toner) =====
('The Ordinary','Glycolic Acid 7% Toning Solution','Exfoliant','2025-07-01','2025-08-01',12,'2026-12-01',240,220000,'Pakai 1-2x seminggu'),

-- ===== Moisturizer =====
('Skintific','5X Ceramide Barrier Moisture Gel','Moisturizer','2025-11-05','2025-11-06',12,'2027-03-01',30,135000,'Kulit kadang perih'),
('Simple','Hydrating Light Moisturiser','Moisturizer','2025-08-05','2025-08-06',12,'2026-08-01',125,85000,''),
('La Roche-Posay','Cicaplast Baume B5','Moisturizer','2025-10-30','2025-11-01',12,'2027-05-01',40,175000,'Recovery'),
('Vaseline','Petroleum Jelly','Moisturizer','2025-01-10','2025-02-01',36,'2028-01-01',50,25000,'Occlusive tipis'),
('Etude','SoonJung 2x Barrier Intensive Cream','Moisturizer','2025-11-18','2025-11-20',12,'2027-04-01',60,210000,'Kulit sensitif'),
('CeraVe','Moisturizing Cream','Moisturizer','2025-10-22','2025-10-25',12,'2027-04-01',340,320000,'Body/face (hemat)'),
('Azarine','Oil Free Brightening Moisturizer','Moisturizer','2025-12-08','2025-12-09',12,'2027-06-01',40,65000,'Moisturizer ringan'),

-- ===== Mask =====
('Innisfree','Jeju Volcanic Pore Clay Mask','Mask','2025-06-25','2025-07-01',12,'2027-03-01',100,180000,'1x/minggu'),
('Whitelab','Mugwort Pore Clarifying Mask','Mask','2025-11-03','2025-11-04',12,'2027-03-01',100,95000,''),

-- ===== Spot Treatment =====
('Klenzit','Clindamycin Gel','Spot Treatment','2025-09-20','2025-09-20',6,'2026-06-01',15,65000,'Jerawat'),
('Benzolac','Benzoyl Peroxide 2.5%','Spot Treatment','2025-10-12','2025-10-12',6,'2026-08-01',20,75000,'Tipis');