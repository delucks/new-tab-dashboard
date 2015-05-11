create table if not exists Stats(
  load_avg_1 double(4) not null,
  load_avg_5 double(4) not null,
  load_avg_15 double(4) not null,
  mem_total int(20) not null,
  mem_buffers int(20) not null,
  mem_free int(20) not null,
  mem_cache int(20) not null,
  mem_swap int(20) not null,
  mem_active int(20) not null,
  timestamp datetime default CURRENT_TIMESTAMP,
  primary key (timestamp)
);
