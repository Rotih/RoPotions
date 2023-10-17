create table
  public.carts (
    cart_id integer generated by default as identity,
    customer text not null,
    constraint cart_pkey primary key (cart_id)
  ) tablespace pg_default;

create table
  public.global_inventory (
    id integer generated by default as identity,
    gold integer not null,
    num_red_ml integer not null default 0,
    num_green_ml integer not null default 0,
    num_blue_ml integer not null default 0,
    constraint global_inventory_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.potion_inventory (
    id integer generated by default as identity,
    sku text not null,
    quantity integer not null,
    price integer not null,
    red integer not null,
    green integer not null,
    blue integer not null,
    dark integer not null,
    constraint potion_types_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.cart_items (
    id bigint generated by default as identity,
    cart_id integer not null,
    potion_id integer not null,
    quantity integer not null default 0,
    constraint cart_items_pkey primary key (id),
    constraint cart_items_cart_id_fkey foreign key (cart_id) references carts (cart_id),
    constraint cart_items_potion_id_fkey foreign key (potion_id) references potions (id)
  ) tablespace pg_default;