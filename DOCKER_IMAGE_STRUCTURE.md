# Docker Image Internal File Structure (gdp-assistant:latest)

This document captures the complete internal layout and file structure packaged inside the unified single Docker image.

## /app (FastAPI AI Engine, OCR Worker, Services & Schemas)
```text
├── Dockerfile  (1,748 bytes)
├── HANDOFF.md  (6,876 bytes)
├── README.md  (3,466 bytes)
├── __init__.py  (22 bytes)
├── alembic/
│   ├── env.py  (1,711 bytes)
│   ├── script.py.mako  (635 bytes)
│   └── versions/
│       ├── 001_initial_schema.py  (10,310 bytes)
│       └── 002_production_hardening.py  (2,812 bytes)
├── alembic.ini  (661 bytes)
├── app/
│   ├── __init__.py  (18 bytes)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py  (240 bytes)
│   │   │   ├── auth.py  (996 bytes)
│   │   │   ├── documents.py  (5,178 bytes)
│   │   │   └── status.py  (1,248 bytes)
│   │   └── v1/
│   │       └── translate.py  (518 bytes)
│   ├── config.py  (5,280 bytes)
│   ├── database/
│   │   ├── connection.py  (1,813 bytes)
│   │   └── models.py  (1,620 bytes)
│   ├── dependencies.py  (5,538 bytes)
│   ├── main.py  (14,802 bytes)
│   ├── models/
│   │   └── document.py  (115 bytes)
│   ├── queue/
│   │   └── redis_queue.py  (1,048 bytes)
│   ├── routers/
│   │   ├── admin.py  (98,798 bytes)
│   │   ├── grievance.py  (41,119 bytes)
│   │   ├── petitions.py  (10,473 bytes)
│   │   ├── search.py  (2,193 bytes)
│   │   └── translate.py  (5,476 bytes)
│   ├── schemas/
│   │   ├── document.py  (991 bytes)
│   │   └── ocr.py  (864 bytes)
│   └── services/
│       ├── extraction_service.py  (3,666 bytes)
│       ├── ocr_service.py  (7,483 bytes)
│       ├── report_document_service.py  (49,397 bytes)
│       ├── validation_service.py  (1,956 bytes)
│       └── verification_service.py  (991 bytes)
├── backups/
│   └── dro_enterprise_backup_20260925_122519.tar.gz  (30,685,435 bytes)
├── core/
│   ├── __init__.py  (19 bytes)
│   ├── llm_client.py  (18,999 bytes)
│   ├── security.py  (3,214 bytes)
│   └── security_config.py  (4,658 bytes)
├── data/
│   └── erode_administrative_hierarchy.json  (31,766 bytes)
├── init_db.py  (2,264 bytes)
├── model_cache/
│   ├── CACHEDIR.TAG  (191 bytes)
│   ├── blobs/
│   │   ├── 40/
│   │   │   ├── 4042e40873843d80568f133b625a04b27e90a6536b9abc2df10225fcd454a851  (9,081,518 bytes)
│   │   │   ├── 4042e40873843d80568f133b625a04b27e90a6536b9abc2df10225fcd454a851.lock  (0 bytes)
│   │   │   └── 4042e40873843d80568f133b625a04b27e90a6536b9abc2df10225fcd454a851.refs  (140 bytes)
│   │   └── b8/
│   │       ├── b843f68c48263ac9fc3ea8f55e59bed7065194bf524cb2ae67542dbe1c329c10  (470,641,600 bytes)
│   │       ├── b843f68c48263ac9fc3ea8f55e59bed7065194bf524cb2ae67542dbe1c329c10.lock  (0 bytes)
│   │       └── b843f68c48263ac9fc3ea8f55e59bed7065194bf524cb2ae67542dbe1c329c10.refs  (140 bytes)
│   ├── models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/
│   │   ├── blobs/
│   │   │   ├── 2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8  (9,081,518 bytes)
│   │   │   ├── 2ea7ad0e45a9d1d1591782ba7e29a703d0758831  (239 bytes)
│   │   │   ├── 3c1b565ae10a15a1d0c31096f834af2fd9359e91  (526 bytes)
│   │   │   ├── 5fd10429389515d3e5cccdeda08cae5fea1ae82e  (53 bytes)
│   │   │   ├── 6bedb7f3622d56b7020f33ab93f6996d33242043  (3,888 bytes)
│   │   │   ├── b974b349cb2d419ada11181750a733ff82f291ad  (122 bytes)
│   │   │   ├── c06d5b49495f044e6380e68a60538be17a6bd5d1  (645 bytes)
│   │   │   ├── d1514c3162bbe87b343f565fadc62e6c06f04f03  (190 bytes)
│   │   │   ├── eaa086f0ffee582aeb45b36e34cdd1fe2d6de2bef61f8a559a1bbc9bd955917b  (470,641,600 bytes)
│   │   │   └── f7640f94e81bb7f4f04daf1668850b38763a13d9  (229 bytes)
│   │   ├── refs/
│   │   │   └── main  (40 bytes)
│   │   └── snapshots/
│   │       └── e8f8c211226b894fcb81acc59f3b34ba3efd5f42/
│   └── xet/
│       ├── https___cas_serv-tGqkUaZf_CBPHQ6h/
│       │   └── staging/
│       └── logs/
│           ├── xet_20260926T122535266+0000_19.log  (61,586 bytes)
│           └── xet_20260926T122612241+0000_18.log  (35,771 bytes)
├── models/
│   ├── __init__.py  (21 bytes)
│   ├── database.py  (26,044 bytes)
│   ├── orm.py  (13,909 bytes)
│   └── schemas.py  (9,874 bytes)
├── requirements.txt  (2,565 bytes)
├── scripts/
│   ├── backup_db.py  (4,603 bytes)
│   ├── build_taxonomy.py  (1,717 bytes)
│   ├── check_db.py  (1,292 bytes)
│   ├── generate_hierarchy_json.py  (25,154 bytes)
│   ├── ingest_nambiyur_and_blocks.py  (26,320 bytes)
│   ├── inspect_pg.py  (630 bytes)
│   ├── manage_db.py  (22,624 bytes)
│   ├── migrate_all_to_postgres.py  (33,970 bytes)
│   ├── test_live_endpoints.py  (2,039 bytes)
│   └── update_schema.py  (4,095 bytes)
├── services/
│   ├── __init__.py  (23 bytes)
│   ├── ai_analyzer.py  (99,887 bytes)
│   ├── cm_grievance_rag.py  (18,099 bytes)
│   ├── court_checker.py  (7,761 bytes)
│   ├── entity_extractor.py  (84,282 bytes)
│   ├── file_store.py  (5,069 bytes)
│   ├── geo_validator.py  (24,791 bytes)
│   ├── job_queue.py  (14,486 bytes)
│   ├── location_matcher.py  (35,182 bytes)
│   ├── master_data_seeder.py  (78,968 bytes)
│   ├── ocr_router.py  (33,786 bytes)
│   ├── prompt_builder.py  (2,635 bytes)
│   ├── semantic_cache.py  (10,242 bytes)
│   ├── tamil_chunker.py  (3,127 bytes)
│   ├── taxonomy_matcher.py  (25,307 bytes)
│   ├── vector_store.py  (14,606 bytes)
│   └── verification_barrier.py  (5,088 bytes)
├── static/
│   └── media/
│       ├── 03281135-8580-4949-827d-03a987312d83_p1.png  (184,726 bytes)
│       ├── 0c0eb2d9-3b44-4541-b729-fcb61548af73_p1.png  (184,538 bytes)
│       ├── 0c449b99-f045-4ca2-9111-2af71664a82e_p1.png  (1,085,224 bytes)
│       ├── 10e7d199-523e-4704-94d0-0de6a7f86b78_p1.png  (184,194 bytes)
│       ├── 118c3fe1-4b13-45c2-ade0-0a48f6436ed5_p1.png  (180,903 bytes)
│       ├── 132f60db-bad3-45cc-9691-fcce5548b058_p1.png  (184,726 bytes)
│       ├── 151e0786-4a09-434c-bc48-ef288e8d5b7a_p1.png  (180,004 bytes)
│       ├── 16663e6e-e5c5-4308-9a5e-808cb009a60e_p1.png  (2,512,940 bytes)
│       ├── 185a68dc-ca79-4ad2-ba4f-b13122dc9afa_p1.png  (11,315,064 bytes)
│       ├── 1874cec3-0f85-4140-8936-cd5ad3648181_p1.png  (184,538 bytes)
│       ├── 1bec3446-5a99-42e5-8be3-550ba14c9f83_p1.png  (180,004 bytes)
│       ├── 1c8e9e66-aae8-49c5-a506-231c68351c36_p1.png  (180,981 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p1.png  (1,915,711 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p1.png_opt.png  (507,719 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p2.png  (1,640,779 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p2.png_opt.png  (430,314 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p3.png  (811,555 bytes)
│       ├── 1d4dc1de-5f44-4138-8274-7f5ce345e6ec_p3.png_opt.png  (214,395 bytes)
│       ├── 1d653dd7-7905-4c77-93e9-a7b94a27fcc9_p1.png  (180,740 bytes)
│       ├── 1db74301-14db-459c-83f8-1d18ea8e92f2_p1.png  (9,759,170 bytes)
│       ├── 22e6d2ef-7db3-4f9b-b6cb-3191ff1e4f67_p1.png  (184,538 bytes)
│       ├── 24aebbc2-3acb-4edd-bb68-89d3ca0af4da_p1.png  (180,981 bytes)
│       ├── 24cdf542-0b00-442e-926d-732611a3729b_p1.png  (180,740 bytes)
│       ├── 268f776c-e977-4a6e-8148-049cc93f8b1a_p1.png  (2,153,157 bytes)
│       ├── 290d0765-0c01-42fe-be37-3c5cd5b514f0_p1.png  (180,004 bytes)
│       ├── 29a51f04-7569-4684-a4b1-fee4b3e1f218_p1.png  (180,740 bytes)
│       ├── 2a942c30-1bc7-496c-b34e-76cacf24efbb_p1.png  (1,559,135 bytes)
│       ├── 2c5e689f-9ca1-4bd1-83e3-6df031d1e8a0_p1.png  (8,265,484 bytes)
│       ├── 2d32afe3-cc0b-49b5-8048-5edc0e406627_p1.png  (180,877 bytes)
│       ├── 2dbeb39a-5486-45b4-b339-20d9193fb3dd_p1.png  (184,194 bytes)
│       ├── 2f1664aa-5e92-4a8d-bdb9-8579c55aa35a_p1.png  (9,575,466 bytes)
│       ├── 31880d61-851a-486e-9551-c1dbd3459306_p1.png  (184,726 bytes)
│       ├── 3c40daf8-4cd8-44c7-ada7-e2d984369629_p1.png  (180,740 bytes)
│       ├── 40ad5572-7a84-4034-93af-0dafdf078454_p1.png  (1,471,249 bytes)
│       ├── 41c7f517-7620-40dc-ab5a-ab1c630cd6b3_p1.png  (1,915,711 bytes)
│       ├── 41c7f517-7620-40dc-ab5a-ab1c630cd6b3_p2.png  (1,640,779 bytes)
│       ├── 41c7f517-7620-40dc-ab5a-ab1c630cd6b3_p3.png  (811,555 bytes)
│       ├── 43e64193-a3b1-4f4e-9bc9-91d90987da68_p1.png  (2,787 bytes)
│       ├── 4432dcb5-175e-4962-a050-cd18da4f0a3c_p1.png  (5,444,324 bytes)
│       ├── 468a4ac9-3f76-4324-9e66-e2820668eb9c_p1.png  (184,538 bytes)
│       ├── 483f02dc-ba79-468e-872c-0f7011a9c7c8_p1.png  (180,740 bytes)
│       ├── 4ec834f3-2f14-4601-92dd-b193f69584ef_p1.png  (184,194 bytes)
│       ├── 52fd3280-3e62-43ef-82cf-3b8502fc9169_p1.png  (184,194 bytes)
│       ├── 561ca9b2-3846-4855-9749-feb2cf50eefa_p1.png  (180,004 bytes)
│       ├── 56c19e30-42e4-4095-b7c9-8cb3a36b5914_p1.png  (3,065,951 bytes)
│       ├── 56c56b0b-9f74-4c7d-a3f2-5d671ef9a26f_p1.png  (1,471,249 bytes)
│       ├── 5a9ebbc5-fea9-4258-9107-e9efee2afb9a_p1.png  (184,726 bytes)
│       ├── 5af2a586-c8a5-4924-b7e3-ff3fc3a4e91d_p1.png  (11,160,576 bytes)
│       ├── 5f480291-0646-42c3-a089-0287ef688e4a_p1.png  (180,004 bytes)
│       ├── 608b7ef3-589e-44ae-8b6e-8a3dd85c683f_p1.png  (184,538 bytes)
│       ├── 609549d5-ddff-4c60-bab6-025c5e7b9729_p1.png  (180,903 bytes)
│       ├── 67019986-b85a-45c6-b815-e388557cd5cf_p1.png  (1,656,242 bytes)
│       ├── 6b6e7cf7-109c-4411-8d87-a947dd0792ef_p1.png  (180,903 bytes)
│       ├── 6da6bc91-b073-42f2-bc2a-e1b105676434_p1.png  (2,110,717 bytes)
│       ├── 6e48c28b-5d76-4379-9458-24d2ded8f5b1_p1.png  (184,538 bytes)
│       ├── 74bbf569-16a7-4add-a1d0-9b6ce06698cf_p1.png  (184,726 bytes)
│       ├── 765e6dd3-9bd5-4c94-a6de-63c1c21db3cc_p1.png  (184,194 bytes)
│       ├── 7f69aa0a-b770-498c-9fda-fedf5bab0fbc_p1.png  (1,870,976 bytes)
│       ├── 8363dfb0-0c33-4c28-bbb0-ab0f6f243874_p1.png  (184,538 bytes)
│       ├── 83f5f671-9653-4670-b402-f040c663896e_p1.png  (180,903 bytes)
│       ├── 8b36887d-f7dd-43f3-abd1-b389cab10d63_p1.png  (180,740 bytes)
│       ├── 90c8fc0b-34e9-4d05-bcab-ff38ad5d007f_p1.png  (180,004 bytes)
│       ├── 93e40af4-33ad-475c-9051-b0a0a7750c9c_p1.png  (1,559,135 bytes)
│       ├── 97694170-2f19-423e-b398-d3376328e78d_p1.png  (184,538 bytes)
│       ├── 9911ee58-0eeb-4686-aad0-c39c10bf250c_p1.png  (1,870,976 bytes)
│       ├── a0b50128-db7b-4054-904b-9ce70653d837_p1.png  (573,707 bytes)
│       ├── a9f34b23-07c1-4860-a29b-3c887edd5419_p1.png  (180,903 bytes)
│       ├── ac18ec98-0119-44a1-834c-e93754ce23d7_p1.png  (180,740 bytes)
│       ├── ad2d89fa-acbf-447d-a85c-03358611354d_p1.png  (180,903 bytes)
│       ├── b77c55d5-b03f-487c-b123-f9bdff33e67b_p1.png  (180,017 bytes)
│       ├── b81d01a8-ed14-4286-95b7-7ca7ceb2b974_p1.png  (180,004 bytes)
│       ├── b9593a56-449a-4fa7-a0ba-54877121e4b8_p1.png  (184,726 bytes)
│       ├── bb6523d8-114d-4f32-a80d-7d07fa62fa52_p1.png  (2,637,299 bytes)
│       ├── bb6523d8-114d-4f32-a80d-7d07fa62fa52_p2.png  (2,110,880 bytes)
│       ├── bb6523d8-114d-4f32-a80d-7d07fa62fa52_p3.png  (1,677,701 bytes)
│       ├── bb6523d8-114d-4f32-a80d-7d07fa62fa52_p4.png  (1,872,068 bytes)
│       ├── bc81526f-8a62-4aed-93eb-0714ae83a40e_p1.png  (639,906 bytes)
│       ├── be3ca63c-a520-4422-b3a2-96a95669e860_p1.png  (180,903 bytes)
│       ├── bebb036b-8856-4c1c-adc7-4c4d92c860a3_p1.png  (184,194 bytes)
│       ├── bff116bb-f1e3-4ad7-951a-c873d62f4a39_p1.png  (1,241,752 bytes)
│       ├── c949dba0-5f66-4265-abfb-cc8e42593c3e_p1.png  (184,194 bytes)
│       ├── cc9f6c81-5762-45a6-bb14-3d3d11658c5b_p1.png  (184,538 bytes)
│       ├── d3fc5705-245e-4784-9c9f-81181582e4ed_p1.png  (184,194 bytes)
│       ├── d77c4813-b373-4847-ae8e-c753e4aecc28_p1.png  (1,085,224 bytes)
│       ├── d902a0ca-2ebf-4623-b3ae-97944540bc0a_p1.png  (184,726 bytes)
│       ├── db491b38-e890-4472-be12-5cd2d2cd46f3_p1.png  (180,903 bytes)
│       ├── dd33be78-1b20-4710-9d78-d12704f82f0f_p1.png  (184,538 bytes)
│       ├── dde03c32-f6af-4d89-8590-442688f80feb_p1.png  (180,740 bytes)
│       ├── ddecb225-fca7-4437-9ecd-e162711e67bc_p1.png  (184,538 bytes)
│       ├── def2ae88-6850-4b81-976f-efa78f235c76_p1.png  (184,726 bytes)
│       ├── e216da04-60aa-430c-9839-483f669b8a0c_p1.png  (180,903 bytes)
│       ├── e3753618-16bd-4cd6-a5f1-3d993c060a5e_p1.png  (184,194 bytes)
│       ├── eb9a133f-91e9-4eb3-96bf-c327bd58cfab_p1.png  (184,538 bytes)
│       ├── ec4c82ba-561f-469b-bc3f-658d48b6759f_p1.png  (180,004 bytes)
│       ├── f02c227c-b716-42f4-a34d-f67fcc901726_p1.png  (1,276,534 bytes)
│       ├── f2efdf86-3d7a-471e-8cd2-ff7814fc6150_p1.png  (2,153,157 bytes)
│       ├── f35e3985-1c8e-4756-beca-10b22b63162d_p1.png  (1,656,242 bytes)
│       ├── f35e3985-1c8e-4756-beca-10b22b63162d_p1.png_opt.png  (454,153 bytes)
│       ├── f3a587bb-32fb-44a1-bf93-ec495ec0f97a_p1.png  (12,176,706 bytes)
│       ├── f871777c-54f3-4066-9a60-41ac51e25f9e_p1.png  (3,352,393 bytes)
│       ├── fe19a470-12b8-45db-a343-37309cf15428_p1.png  (184,726 bytes)
│       └── ffaa2cdb-db53-431e-b272-93573d1e4a91_p1.png  (180,740 bytes)
├── storage/
│   └── uploads/
├── temp_cache/
│   ├── backups/
│   ├── dro_admin.db  (2,056,192 bytes)
│   ├── dro_audit.db  (36,864 bytes)
│   ├── dro_user.db  (102,400 bytes)
│   └── torchinductor_root/
├── uploads/
└── worker/
    ├── __init__.py  (58 bytes)
    └── ocr_worker.py  (5,547 bytes)
`

## /usr/share/nginx/html (React 19 Vite Production UI Bundle)
`	ext
├── assets/
│   ├── index-DJ1-k4k6.js  (473,920 bytes)
│   ├── index-_4H1sqJT.css  (145,652 bytes)
│   └── tn-emblem-transparent-D_310zOs.png  (383,181 bytes)
├── favicon.svg  (9,522 bytes)
├── icons.svg  (5,055 bytes)
├── index.html  (2,302 bytes)
├── robots.txt  (219 bytes)
├── sitemap.xml  (784 bytes)
└── tn-emblem.png  (168,593 bytes)
`

## /etc/supervisor/conf.d (Supervisor Process Manager)
`	ext
└── supervisord.conf  (1,175 bytes)
`

## /etc/nginx/conf.d (Nginx Reverse Proxy & Static Server)
`	ext
└── default.conf  (1,618 bytes)
`

