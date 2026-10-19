-- =====================================================================
-- TiendaLocal — esquema vigente de la base de datos
--
-- ARCHIVO GENERADO. No se edita a mano.
--
-- La fuente de verdad son las migraciones de Alembic en backend/alembic/.
-- Este volcado existe solo para leer el esquema completo de un tirón, sin
-- reconstruirlo mentalmente a partir de la cadena de revisiones (ADR-009).
--
-- Regenerar (con la base ya migrada a head):
--   pg_dump --schema-only --no-owner --no-privileges --no-comments \
--     | grep -vE '^(--Dumped|\\(un)?restrict)'
--
-- Se quitan del volcado las líneas \restrict/\unrestrict y el sello de fecha:
-- cambian en cada ejecución y harían que este archivo apareciera modificado
-- sin que el esquema haya cambiado.
--
-- Si este archivo y las migraciones difieren, este archivo es el que miente.
-- =====================================================================

--
-- PostgreSQL database dump
--



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;


--
-- Name: f_unaccent(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    AS $_$ SELECT public.unaccent('public.unaccent', $1) $_$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_user (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(160) NOT NULL,
    password_hash text NOT NULL,
    full_name character varying(120) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_admin_user_correo_formato CHECK (((email)::text ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)),
    CONSTRAINT ck_admin_user_correo_minusculas CHECK (((email)::text = lower((email)::text))),
    CONSTRAINT ck_admin_user_hash_no_vacio CHECK ((length(TRIM(BOTH FROM password_hash)) > 0))
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    admin_user_id uuid,
    entity_type character varying(30) NOT NULL,
    entity_id uuid NOT NULL,
    action character varying(30) NOT NULL,
    source character varying(20) NOT NULL,
    old_value character varying(120),
    new_value character varying(120) NOT NULL,
    reason character varying(120),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_audit_log_accion_valida CHECK (((action)::text = ANY ((ARRAY['STOCK_CHANGE'::character varying, 'STATUS_CHANGE'::character varying, 'PUBLISH_CHANGE'::character varying])::text[]))),
    CONSTRAINT ck_audit_log_entidad_valida CHECK (((entity_type)::text = ANY ((ARRAY['INVENTORY'::character varying, 'ORDER'::character varying, 'PRODUCT'::character varying])::text[]))),
    CONSTRAINT ck_audit_log_motivo_obligatorio CHECK ((((source)::text = 'ORDEN'::text) OR (reason IS NOT NULL))),
    CONSTRAINT ck_audit_log_origen_valido CHECK (((source)::text = ANY ((ARRAY['AJUSTE_MANUAL'::character varying, 'ORDEN'::character varying, 'CANCELACION'::character varying])::text[]))),
    CONSTRAINT ck_audit_log_valor_nuevo_no_vacio CHECK ((length(TRIM(BOTH FROM new_value)) > 0))
);


--
-- Name: category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.category (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(80) NOT NULL,
    slug character varying(90) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_category_nombre_minimo CHECK ((length((name)::text) >= 2)),
    CONSTRAINT ck_category_slug_formato CHECK (((slug)::text ~ '^[a-z0-9-]+$'::text))
);


--
-- Name: inventory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory (
    variant_id uuid NOT NULL,
    stock_quantity integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_inventory_stock_no_negativo CHECK ((stock_quantity >= 0))
);


--
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    recipient_type character varying(20) NOT NULL,
    recipient character varying(160) NOT NULL,
    status character varying(20) DEFAULT 'PENDIENTE'::character varying NOT NULL,
    attempts smallint DEFAULT 0 NOT NULL,
    last_error character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    sent_at timestamp with time zone,
    CONSTRAINT ck_notification_correo_formato CHECK (((recipient)::text ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)),
    CONSTRAINT ck_notification_destinatario_valido CHECK (((recipient_type)::text = ANY ((ARRAY['COMPRADOR'::character varying, 'ADMINISTRADOR'::character varying])::text[]))),
    CONSTRAINT ck_notification_estado_valido CHECK (((status)::text = ANY ((ARRAY['PENDIENTE'::character varying, 'ENVIADA'::character varying, 'FALLIDA'::character varying])::text[]))),
    CONSTRAINT ck_notification_intentos_no_negativos CHECK ((attempts >= 0))
);


--
-- Name: order_header; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_header (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_number character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'CONFIRMADA'::character varying NOT NULL,
    total_cop bigint NOT NULL,
    customer_name character varying(120) NOT NULL,
    customer_email character varying(160) NOT NULL,
    customer_phone character varying(20) NOT NULL,
    shipping_address character varying(200) NOT NULL,
    shipping_city character varying(80) NOT NULL,
    data_processing_consent boolean NOT NULL,
    privacy_notice_version character varying(20) NOT NULL,
    consent_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_order_header_ciudad_no_vacia CHECK ((length(TRIM(BOTH FROM shipping_city)) > 0)),
    CONSTRAINT ck_order_header_consentimiento_obligatorio CHECK ((data_processing_consent = true)),
    CONSTRAINT ck_order_header_correo_formato CHECK (((customer_email)::text ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)),
    CONSTRAINT ck_order_header_direccion_no_vacia CHECK ((length(TRIM(BOTH FROM shipping_address)) > 0)),
    CONSTRAINT ck_order_header_estado_valido CHECK (((status)::text = ANY ((ARRAY['CONFIRMADA'::character varying, 'PREPARADA'::character varying, 'ENTREGADA'::character varying, 'CANCELADA'::character varying])::text[]))),
    CONSTRAINT ck_order_header_nombre_no_vacio CHECK ((length(TRIM(BOTH FROM customer_name)) > 0)),
    CONSTRAINT ck_order_header_numero_formato CHECK (((order_number)::text ~ '^TL-[0-9]{8}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{5}$'::text)),
    CONSTRAINT ck_order_header_telefono_formato CHECK (((customer_phone)::text ~ '^[0-9]{7,15}$'::text)),
    CONSTRAINT ck_order_header_total_positivo CHECK ((total_cop > 0))
);


--
-- Name: order_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_item (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    product_name character varying(120) NOT NULL,
    size character varying(20) NOT NULL,
    quantity integer NOT NULL,
    unit_price_cop bigint NOT NULL,
    line_total_cop bigint NOT NULL,
    CONSTRAINT ck_order_item_cantidad_positiva CHECK ((quantity > 0)),
    CONSTRAINT ck_order_item_precio_positivo CHECK ((unit_price_cop > 0)),
    CONSTRAINT ck_order_item_total_linea_coherente CHECK ((line_total_cop = (quantity * unit_price_cop)))
);


--
-- Name: product; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    category_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    slug character varying(140) NOT NULL,
    description text,
    price_cop bigint NOT NULL,
    published boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_product_descripcion_maxima CHECK (((description IS NULL) OR (length(description) <= 2000))),
    CONSTRAINT ck_product_nombre_minimo CHECK ((length((name)::text) >= 3)),
    CONSTRAINT ck_product_precio_positivo CHECK ((price_cop > 0)),
    CONSTRAINT ck_product_slug_formato CHECK (((slug)::text ~ '^[a-z0-9-]+$'::text))
);


--
-- Name: product_image; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_image (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    url text NOT NULL,
    alt_text character varying(160) NOT NULL,
    "position" smallint DEFAULT 0 NOT NULL,
    width smallint NOT NULL,
    height smallint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_product_image_alt_text_no_vacio CHECK ((length(TRIM(BOTH FROM alt_text)) > 0)),
    CONSTRAINT ck_product_image_alto_positivo CHECK ((height > 0)),
    CONSTRAINT ck_product_image_ancho_positivo CHECK ((width > 0)),
    CONSTRAINT ck_product_image_posicion_no_negativa CHECK (("position" >= 0)),
    CONSTRAINT ck_product_image_url_no_vacia CHECK ((length(TRIM(BOTH FROM url)) > 0))
);


--
-- Name: product_variant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_variant (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    sku character varying(40) NOT NULL,
    size character varying(20) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_product_variant_sku_formato CHECK (((sku)::text ~ '^[A-Z0-9-]+$'::text))
);


--
-- Name: size_catalog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.size_catalog (
    code character varying(20) NOT NULL,
    label character varying(40) NOT NULL,
    "position" smallint NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_size_catalog_codigo_mayusculas CHECK (((code)::text = upper((code)::text))),
    CONSTRAINT ck_size_catalog_etiqueta_no_vacia CHECK ((length(TRIM(BOTH FROM label)) > 0)),
    CONSTRAINT ck_size_catalog_posicion_no_negativa CHECK (("position" >= 0))
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: admin_user pk_admin_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_user
    ADD CONSTRAINT pk_admin_user PRIMARY KEY (id);


--
-- Name: audit_log pk_audit_log; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT pk_audit_log PRIMARY KEY (id);


--
-- Name: category pk_category; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT pk_category PRIMARY KEY (id);


--
-- Name: inventory pk_inventory; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT pk_inventory PRIMARY KEY (variant_id);


--
-- Name: notification pk_notification; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT pk_notification PRIMARY KEY (id);


--
-- Name: order_header pk_order_header; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_header
    ADD CONSTRAINT pk_order_header PRIMARY KEY (id);


--
-- Name: order_item pk_order_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT pk_order_item PRIMARY KEY (id);


--
-- Name: product pk_product; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT pk_product PRIMARY KEY (id);


--
-- Name: product_image pk_product_image; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_image
    ADD CONSTRAINT pk_product_image PRIMARY KEY (id);


--
-- Name: product_variant pk_product_variant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variant
    ADD CONSTRAINT pk_product_variant PRIMARY KEY (id);


--
-- Name: size_catalog pk_size_catalog; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_catalog
    ADD CONSTRAINT pk_size_catalog PRIMARY KEY (code);


--
-- Name: admin_user uq_admin_user_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_user
    ADD CONSTRAINT uq_admin_user_email UNIQUE (email);


--
-- Name: category uq_category_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT uq_category_name UNIQUE (name);


--
-- Name: category uq_category_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT uq_category_slug UNIQUE (slug);


--
-- Name: order_header uq_order_header_order_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_header
    ADD CONSTRAINT uq_order_header_order_number UNIQUE (order_number);


--
-- Name: order_item uq_order_item_order_id_variant_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT uq_order_item_order_id_variant_id UNIQUE (order_id, variant_id);


--
-- Name: product_image uq_product_image_product_id_position; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_image
    ADD CONSTRAINT uq_product_image_product_id_position UNIQUE (product_id, "position");


--
-- Name: product uq_product_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT uq_product_slug UNIQUE (slug);


--
-- Name: product_variant uq_product_variant_product_id_size; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variant
    ADD CONSTRAINT uq_product_variant_product_id_size UNIQUE (product_id, size);


--
-- Name: product_variant uq_product_variant_sku; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variant
    ADD CONSTRAINT uq_product_variant_sku UNIQUE (sku);


--
-- Name: size_catalog uq_size_catalog_position; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.size_catalog
    ADD CONSTRAINT uq_size_catalog_position UNIQUE ("position");


--
-- Name: idx_product_name_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_product_name_search ON public.product USING gin (lower(public.f_unaccent((name)::text)) public.gin_trgm_ops);


--
-- Name: ix_audit_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_created_at ON public.audit_log USING btree (created_at DESC);


--
-- Name: ix_audit_log_entity_type_entity_id_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_entity_type_entity_id_created_at ON public.audit_log USING btree (entity_type, entity_id, created_at DESC);


--
-- Name: ix_notification_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_order_id ON public.notification USING btree (order_id);


--
-- Name: ix_notification_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_status ON public.notification USING btree (status);


--
-- Name: ix_order_header_customer_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_header_customer_email ON public.order_header USING btree (lower((customer_email)::text));


--
-- Name: ix_order_header_status_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_header_status_created_at ON public.order_header USING btree (status, created_at DESC);


--
-- Name: ix_order_item_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_item_order_id ON public.order_item USING btree (order_id);


--
-- Name: ix_product_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_category_id ON public.product USING btree (category_id);


--
-- Name: ix_product_image_product_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_image_product_id ON public.product_image USING btree (product_id);


--
-- Name: ix_product_published; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_published ON public.product USING btree (published);


--
-- Name: ix_product_variant_product_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_variant_product_id ON public.product_variant USING btree (product_id);


--
-- Name: ix_product_variant_size; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_variant_size ON public.product_variant USING btree (size);


--
-- Name: audit_log fk_audit_log_admin_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT fk_audit_log_admin_user_id FOREIGN KEY (admin_user_id) REFERENCES public.admin_user(id) ON DELETE RESTRICT;


--
-- Name: inventory fk_inventory_variant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT fk_inventory_variant_id FOREIGN KEY (variant_id) REFERENCES public.product_variant(id) ON DELETE RESTRICT;


--
-- Name: notification fk_notification_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT fk_notification_order_id FOREIGN KEY (order_id) REFERENCES public.order_header(id) ON DELETE RESTRICT;


--
-- Name: order_item fk_order_item_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT fk_order_item_order_id FOREIGN KEY (order_id) REFERENCES public.order_header(id) ON DELETE RESTRICT;


--
-- Name: order_item fk_order_item_variant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT fk_order_item_variant_id FOREIGN KEY (variant_id) REFERENCES public.product_variant(id) ON DELETE RESTRICT;


--
-- Name: product fk_product_category_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT fk_product_category_id FOREIGN KEY (category_id) REFERENCES public.category(id) ON DELETE RESTRICT;


--
-- Name: product_image fk_product_image_product_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_image
    ADD CONSTRAINT fk_product_image_product_id FOREIGN KEY (product_id) REFERENCES public.product(id) ON DELETE CASCADE;


--
-- Name: product_variant fk_product_variant_product_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variant
    ADD CONSTRAINT fk_product_variant_product_id FOREIGN KEY (product_id) REFERENCES public.product(id) ON DELETE RESTRICT;


--
-- Name: product_variant fk_product_variant_size; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variant
    ADD CONSTRAINT fk_product_variant_size FOREIGN KEY (size) REFERENCES public.size_catalog(code) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--



-- Semilla del catálogo de tallas, incluida en la migración inicial
-- porque es parte del esquema y no de los datos de prueba (ADR-008).
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('XS', 'XS', 10, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('S', 'S', 20, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('M', 'M', 30, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('L', 'L', 40, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('XL', 'XL', 50, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('XXL', 'XXL', 60, true, '2026-09-27 13:58:23.530558-05');
INSERT INTO public.size_catalog (code, label, "position", active, created_at) VALUES ('ÚNICA', 'Única', 90, true, '2026-09-27 13:58:23.530558-05');
