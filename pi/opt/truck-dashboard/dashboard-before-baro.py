#!/usr/bin/env python3

import json
import math
import os
import time
from pathlib import Path

import pygame


WIDTH = 1024
HEIGHT = 600

LIVE_FILE = Path("/run/truck-telemetry/live.json")
STALE_SECONDS = 5.0


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
    pygame.mouse.set_visible(False)

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.FULLSCREEN,
    )

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

    running = True

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

        data = load_live_data()

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

        if boost is None:
            map_kpa = data.get("map_kpa")

            if map_kpa is not None:
                # Indoor/demo fallback only.
                # Real telemetry will use learned KOEO BARO.
                boost = (
                    float(map_kpa) - 84.5
                ) * 0.1450377

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

        pygame.display.flip()
        clock.tick(20)

    pygame.quit()


if __name__ == "__main__":
    main()
