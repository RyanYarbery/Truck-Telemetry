#!/usr/bin/env python3

import json
import math
import os
import time
from collections import deque
from pathlib import Path

import pygame


WIDTH = 1024
HEIGHT = 600

LIVE_FILE = Path("/run/truck-telemetry/live.json")
STALE_SECONDS = 5.0

BARO_FILE = Path("/var/lib/truck-dashboard/baro.json")
CONTROL_FILE = Path("/var/lib/truck-telemetry/control.json")

DEFAULT_BARO_KPA = 84.5
KPA_TO_PSI = 0.1450377377


def request_trip_reset():
    try:
        CONTROL_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_file = CONTROL_FILE.with_suffix(".tmp")

        temp_file.write_text(
            json.dumps(
                {
                    "reset_trip": True,
                    "requested": time.time(),
                },
                indent=2,
            )
        )

        temp_file.replace(CONTROL_FILE)
        return True

    except Exception as exc:
        print(f"Could not request trip reset: {exc}")
        return False


def load_baro():
    try:
        data = json.loads(BARO_FILE.read_text())
        value = float(data.get("baro_kpa", DEFAULT_BARO_KPA))

        if 70.0 <= value <= 110.0:
            return value

    except Exception:
        pass

    return DEFAULT_BARO_KPA


def save_baro(value):
    try:
        BARO_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_file = BARO_FILE.with_suffix(".tmp")

        temp_file.write_text(
            json.dumps(
                {
                    "baro_kpa": value,
                    "updated": time.time(),
                },
                indent=2,
            )
        )

        temp_file.replace(BARO_FILE)

    except Exception as exc:
        print(f"Could not save BARO: {exc}")


def load_live_data():
    try:
        data = json.loads(LIVE_FILE.read_text())

        timestamp = float(data.get("timestamp", 0))
        age = time.time() - timestamp

        if age <= STALE_SECONDS:
            data["_source"] = "LIVE"
            data["_stale"] = False
            return data

        data["_source"] = "STALE"
        data["_stale"] = True
        return data

    except Exception:
        return simulated_data()


def simulated_data():
    t = time.monotonic()

    rpm = 1500 + math.sin(t * 0.7) * 600
    speed = 42 + math.sin(t * 0.25) * 8
    icp = 750 + math.sin(t * 0.55) * 250
    ipr = 15 + math.sin(t * 0.45) * 4
    eot = 188 + math.sin(t * 0.08) * 3
    tft = 145 + math.sin(t * 0.06) * 4
    voltage = 14.2 + math.sin(t * 0.4) * 0.1
    boost = 5 + math.sin(t * 0.5) * 4
    gph = 2.1 + math.sin(t * 0.35) * 0.7

    if gph > 0:
        mpg = speed / gph
    else:
        mpg = None

    return {
        "_source": "DEMO",
        "_stale": False,
        "rpm": rpm,
        "speed_mph": speed,
        "icp_psi": icp,
        "ipr_pct": ipr,
        "eot_f": eot,
        "tft_f": tft,
        "voltage": voltage,
        "boost_psi": boost,
        "gph": gph,
        "instant_mpg": mpg,
        "trip_miles": 23.7,
        "trip_fuel_gal": 1.31,
        "trip_mpg": 18.1,
        "runtime_seconds": 4363,
    }


def format_runtime(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        seconds = 0

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def value_text(value, decimals=0, missing="---"):
    if value is None:
        return missing

    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return missing


def draw_box(screen, rect, title, value, unit, font_title, font_value, font_unit):
    pygame.draw.rect(screen, (22, 26, 31), rect, border_radius=10)
    pygame.draw.rect(screen, (55, 64, 73), rect, width=2, border_radius=10)

    title_surface = font_title.render(title, True, (170, 180, 190))
    screen.blit(
        title_surface,
        (rect.x + 14, rect.y + 10),
    )

    value_surface = font_value.render(str(value), True, (245, 245, 245))
    value_rect = value_surface.get_rect(
        center=(rect.centerx, rect.centery + 10)
    )
    screen.blit(value_surface, value_rect)

    if unit:
        unit_surface = font_unit.render(unit, True, (150, 160, 170))
        unit_rect = unit_surface.get_rect(
            midbottom=(rect.centerx, rect.bottom - 8)
        )
        screen.blit(unit_surface, unit_rect)


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.FULLSCREEN,
    )

    pygame.mouse.set_visible(False)
    pygame.display.set_caption("Truck Telemetry")

    font_title = pygame.font.Font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        20,
    )

    font_value = pygame.font.Font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        43,
    )

    font_unit = pygame.font.Font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        17,
    )

    font_status = pygame.font.Font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        18,
    )

    font_bottom = pygame.font.Font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        20,
    )

    clock = pygame.time.Clock()

    baro_kpa = load_baro()
    koeo_samples = deque(maxlen=8)

    print(f"BARO baseline: {baro_kpa:.2f} kPa")

    running = True
    page = 0
    reset_confirm_until = 0.0
    reset_message_until = 0.0

    page_button = pygame.Rect(12, 545, 150, 44)
    reset_button = pygame.Rect(174, 545, 190, 44)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key in (
                    pygame.K_ESCAPE,
                    pygame.K_q,
                ):
                    running = False

            pointer = None

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    pointer = event.pos

            elif event.type == pygame.FINGERUP:
                pointer = (
                    int(event.x * WIDTH),
                    int(event.y * HEIGHT),
                )

            if pointer is not None:
                if page_button.collidepoint(pointer):
                    page = (page + 1) % 2
                    reset_confirm_until = 0.0

                elif reset_button.collidepoint(pointer):
                    now_touch = time.monotonic()

                    if now_touch <= reset_confirm_until:
                        if request_trip_reset():
                            reset_message_until = now_touch + 2.5

                        reset_confirm_until = 0.0

                    else:
                        reset_confirm_until = now_touch + 4.0

        data = load_live_data()

        # Learn atmospheric pressure during KOEO:
        # PCM responding, RPM == 0, valid MAP.
        if (
            data.get("_source") == "LIVE"
            and not data.get("_stale", False)
        ):
            try:
                rpm_now = float(data.get("rpm"))
                map_now = float(data.get("map_kpa"))

                if (
                    rpm_now <= 1.0
                    and 70.0 <= map_now <= 110.0
                ):
                    koeo_samples.append(map_now)

                    if len(koeo_samples) == koeo_samples.maxlen:
                        candidate = (
                            sum(koeo_samples)
                            / len(koeo_samples)
                        )

                        if abs(candidate - baro_kpa) >= 0.25:
                            baro_kpa = candidate
                            save_baro(baro_kpa)
                            print(
                                "Updated BARO baseline: "
                                f"{baro_kpa:.2f} kPa"
                            )

                        koeo_samples.clear()

                else:
                    koeo_samples.clear()

            except (TypeError, ValueError):
                koeo_samples.clear()

        # Calculate gauge boost from absolute MAP minus BARO.
        if data.get("map_kpa") is not None:
            try:
                boost_psi = (
                    float(data["map_kpa"])
                    - baro_kpa
                ) * KPA_TO_PSI

                # This is a boost gauge rather than a
                # manifold vacuum/pressure gauge.
                data["boost_psi"] = max(
                    0.0,
                    boost_psi,
                )

            except (TypeError, ValueError):
                pass

        data["baro_kpa"] = baro_kpa

        screen.fill((8, 11, 15))

        margin = 12
        gap = 10

        top_y = 42
        box_h = 158

        col_w = (
            WIDTH
            - margin * 2
            - gap * 2
        ) // 3

        row1 = [
            pygame.Rect(
                margin + i * (col_w + gap),
                top_y,
                col_w,
                box_h,
            )
            for i in range(3)
        ]

        row2_y = top_y + box_h + gap

        row2 = [
            pygame.Rect(
                margin + i * (col_w + gap),
                row2_y,
                col_w,
                box_h,
            )
            for i in range(3)
        ]

        status = data.get("_source", "UNKNOWN")

        if status == "LIVE":
            status_color = (80, 220, 120)
            status_text = "OBD LIVE"
        elif status == "DEMO":
            status_color = (240, 190, 70)
            status_text = "DEMO MODE"
        else:
            status_color = (235, 80, 80)
            status_text = "OBD STALE"

        pygame.draw.circle(
            screen,
            status_color,
            (20, 20),
            7,
        )

        status_surface = font_status.render(
            status_text,
            True,
            status_color,
        )

        screen.blit(
            status_surface,
            (34, 10),
        )

        draw_box(
            screen,
            row1[0],
            "RPM",
            value_text(data.get("rpm"), 0),
            "RPM",
            font_title,
            font_value,
            font_unit,
        )

        draw_box(
            screen,
            row1[1],
            "SPEED",
            value_text(data.get("speed_mph"), 0),
            "MPH",
            font_title,
            font_value,
            font_unit,
        )

        boost = data.get("boost_psi")

        draw_box(
            screen,
            row1[2],
            "BOOST",
            value_text(boost, 1),
            "PSI",
            font_title,
            font_value,
            font_unit,
        )

        draw_box(
            screen,
            row2[0],
            "ICP",
            value_text(data.get("icp_psi"), 0),
            "PSI",
            font_title,
            font_value,
            font_unit,
        )

        draw_box(
            screen,
            row2[1],
            "IPR",
            value_text(data.get("ipr_pct"), 1),
            "%",
            font_title,
            font_value,
            font_unit,
        )

        draw_box(
            screen,
            row2[2],
            "VOLTAGE",
            value_text(data.get("voltage"), 1),
            "V",
            font_title,
            font_value,
            font_unit,
        )

        bottom_y = row2_y + box_h + 12

        labels = [
            (
                "EOT",
                f"{value_text(data.get('eot_f'), 0)}°F",
            ),
            (
                "TRANS",
                f"{value_text(data.get('tft_f'), 0)}°F",
            ),
            (
                "GPH",
                value_text(data.get("gph"), 2),
            ),
            (
                "MPG",
                value_text(data.get("instant_mpg"), 1),
            ),
            (
                "TRIP",
                f"{value_text(data.get('trip_miles'), 1)} mi",
            ),
            (
                "AVG",
                f"{value_text(data.get('trip_mpg'), 1)} MPG",
            ),
        ]

        item_w = WIDTH // len(labels)

        for i, (label, value) in enumerate(labels):
            x = i * item_w

            title_surface = font_unit.render(
                label,
                True,
                (150, 160, 170),
            )

            value_surface = font_bottom.render(
                value,
                True,
                (240, 240, 240),
            )

            screen.blit(
                title_surface,
                title_surface.get_rect(
                    center=(x + item_w // 2, bottom_y + 14)
                ),
            )

            screen.blit(
                value_surface,
                value_surface.get_rect(
                    center=(x + item_w // 2, bottom_y + 45)
                ),
            )

        runtime = format_runtime(
            data.get("runtime_seconds", 0)
        )

        runtime_surface = font_unit.render(
            f"Runtime {runtime}",
            True,
            (120, 130, 140),
        )

        screen.blit(
            runtime_surface,
            (
                WIDTH
                - runtime_surface.get_width()
                - 12,
                HEIGHT
                - runtime_surface.get_height()
                - 8,
            ),
        )

        # -------------------------------------------------
        # DETAILS / DIAGNOSTICS PAGE
        # -------------------------------------------------
        if page == 1:
            screen.fill((8, 11, 15))

            # Header
            status = data.get("_source", "UNKNOWN")

            if status == "LIVE":
                status_color = (80, 220, 120)
                status_text = "OBD LIVE"
            elif status == "DEMO":
                status_color = (240, 190, 70)
                status_text = "DEMO MODE"
            else:
                status_color = (235, 80, 80)
                status_text = "OBD STALE"

            pygame.draw.circle(
                screen,
                status_color,
                (20, 20),
                7,
            )

            status_surface = font_status.render(
                status_text,
                True,
                status_color,
            )

            screen.blit(
                status_surface,
                (34, 10),
            )

            title_surface = font_status.render(
                "ENGINE DETAILS",
                True,
                (220, 225, 230),
            )

            screen.blit(
                title_surface,
                title_surface.get_rect(
                    midtop=(WIDTH // 2, 10)
                ),
            )

            # 3 x 3 diagnostics grid
            margin = 12
            gap = 10
            top_y = 48
            box_h = 125

            col_w = (
                WIDTH
                - margin * 2
                - gap * 2
            ) // 3

            details_grid = []

            for row in range(3):
                row_items = []

                for col in range(3):
                    row_items.append(
                        pygame.Rect(
                            margin + col * (col_w + gap),
                            top_y + row * (box_h + gap),
                            col_w,
                            box_h,
                        )
                    )

                details_grid.append(row_items)

            draw_box(
                screen,
                details_grid[0][0],
                "ICP",
                value_text(data.get("icp_psi"), 0),
                "PSI",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[0][1],
                "IPR",
                value_text(data.get("ipr_pct"), 1),
                "%",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[0][2],
                "EOT",
                value_text(data.get("eot_f"), 0),
                "°F",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[1][0],
                "TRANS TEMP",
                value_text(data.get("tft_f"), 0),
                "°F",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[1][1],
                "MAP",
                value_text(data.get("map_kpa"), 0),
                "kPa",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[1][2],
                "BARO",
                value_text(data.get("baro_kpa"), 1),
                "kPa",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[2][0],
                "BOOST",
                value_text(data.get("boost_psi"), 1),
                "PSI",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[2][1],
                "MFDES",
                value_text(data.get("mfdes_mg"), 2),
                "mg/stroke",
                font_title,
                font_value,
                font_unit,
            )

            draw_box(
                screen,
                details_grid[2][2],
                "FUEL PW",
                value_text(data.get("fuel_pw_ms"), 3),
                "ms",
                font_title,
                font_value,
                font_unit,
            )

            # Bottom diagnostic strip
            strip_y = 458

            bottom_details = [
                (
                    "VOLTAGE",
                    f"{value_text(data.get('voltage'), 1)} V",
                ),
                (
                    "FUEL RATE",
                    f"{value_text(data.get('gph'), 2)} GPH",
                ),
                (
                    "RUNTIME",
                    format_runtime(
                        data.get("runtime_seconds", 0)
                    ),
                ),
            ]

            strip_w = WIDTH // 3

            for i, (label, value) in enumerate(bottom_details):
                x = i * strip_w

                label_surface = font_unit.render(
                    label,
                    True,
                    (150, 160, 170),
                )

                value_surface = font_bottom.render(
                    value,
                    True,
                    (240, 240, 240),
                )

                screen.blit(
                    label_surface,
                    label_surface.get_rect(
                        center=(
                            x + strip_w // 2,
                            strip_y,
                        )
                    ),
                )

                screen.blit(
                    value_surface,
                    value_surface.get_rect(
                        center=(
                            x + strip_w // 2,
                            strip_y + 30,
                        )
                    ),
                )

        # -------------------------------------------------
        # Touch controls
        # -------------------------------------------------
        now_ui = time.monotonic()

        button_font = pygame.font.Font(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            18,
        )

        pygame.draw.rect(
            screen,
            (34, 40, 47),
            page_button,
            border_radius=8,
        )
        pygame.draw.rect(
            screen,
            (80, 92, 104),
            page_button,
            width=2,
            border_radius=8,
        )

        page_label = "DETAILS" if page == 0 else "MAIN"

        surf = button_font.render(
            page_label,
            True,
            (240, 240, 240),
        )
        screen.blit(
            surf,
            surf.get_rect(center=page_button.center),
        )

        reset_pending = now_ui <= reset_confirm_until

        if reset_pending:
            reset_bg = (100, 62, 28)
            reset_text = "TAP AGAIN"
        else:
            reset_bg = (45, 42, 42)
            reset_text = "RESET TRIP"

        pygame.draw.rect(
            screen,
            reset_bg,
            reset_button,
            border_radius=8,
        )
        pygame.draw.rect(
            screen,
            (100, 92, 92),
            reset_button,
            width=2,
            border_radius=8,
        )

        surf = button_font.render(
            reset_text,
            True,
            (245, 245, 245),
        )
        screen.blit(
            surf,
            surf.get_rect(center=reset_button.center),
        )

        if now_ui <= reset_message_until:
            message = button_font.render(
                "TRIP RESET REQUESTED",
                True,
                (100, 230, 135),
            )
            screen.blit(
                message,
                (
                    WIDTH - message.get_width() - 14,
                    558,
                ),
            )

        pygame.display.flip()
        clock.tick(20)

    pygame.quit()


if __name__ == "__main__":
    main()
