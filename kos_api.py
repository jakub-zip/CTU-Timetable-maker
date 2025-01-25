import requests
import matplotlib.pyplot as plt
from datetime import datetime, time

import hashlib


def name_to_color(name):
    # Hash the name using SHA256 (or any hash function)
    hash_object = hashlib.sha256(name.encode("utf-8"))
    hex_digest = hash_object.hexdigest()

    # Extract RGB components from the hash
    red = hex_digest[:2]  # First 2 hex digits
    green = hex_digest[2:4]  # Next 2 hex digits
    blue = hex_digest[4:6]  # Following 2 hex digits

    return f"#{red}{green}{blue}"


base = "https://kos.cvut.cz/rest/api/"


class KOSApi:
    def __init__(self, username, password):
        self.s = requests.Session()
        self.s.get("https://kos.cvut.cz/rest/login")
        xsrf_token = self.s.cookies.get("XSRF-TOKEN")
        if xsrf_token:
            self.s.headers["X-XSRF-TOKEN"] = xsrf_token
        login = self.s.post(
            "https://kos.cvut.cz/rest/login",
            data={"username": username, "password": password},
        )
        self.login_data = login.json()

    def get_schedule_course(self, code: str, semester: str):
        try:
            sid = self.s.get(
                base + "course-semesters",
                params={
                    "expanded": "semester",
                    "query": f"semesterId=={semester};code=={code}",
                    "size": 1,
                },
            ).json()["elements"][0]["courseId"]
        except IndexError:
            return []

        timetable = self.s.get(
            base + "timetables/timetable-tickets",
            params={
                "expanded": "parallelClass.teachers,parallelClass.parallelType,room",
                "query": f"courseId=={sid};semesterId=={semester}",
                "size": 0,
            },
        ).json()["elements"]

        # pprint(timetable)

        return [
            {
                "name": code,
                "type": ticket["parallelClass"]["parallelType"]["code"],
                "day": int(ticket["dayNumber"]) - 1,
                "starttime": ticket["ticketStart"],
                "endtime": ticket["ticketEnd"],
                "room": ticket.get("room", {}).get("roomNumber", ""),
                "teachers": ", ".join(
                    map(
                        lambda x: " ".join([x["firstName"], x["lastName"]]),
                        ticket["parallelClass"]["teachers"],
                    )
                ),
                "weeks": ticket.get("evenOddWeek"),
            }
            for ticket in timetable
        ]

    def get_schedule_courses(self, codes: list[str], semester: str):
        out = []
        for code in codes:
            out.extend(self.get_schedule_course(code, semester))
        return out

    def get_semesters(self):
        return self.login_data["studies"][0]["semesters"]

    def get_courses(self):
        courses = self.s.get(
            base + "registered-courses",
            params={
                "query": f"studyId=={self.login_data['studies'][0]['id']}",
                "size": 0,
            },
        ).json()["elements"]

        courses_by_semester = dict()
        for c in courses:
            if c["semester"]["id"] not in courses_by_semester:
                courses_by_semester[c["semester"]["id"]] = []
            courses_by_semester[c["semester"]["id"]].append(c)

        return courses_by_semester


# Days in the week for ordering
days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
days_order = list(range(5))

hour_start_times = [
    time(hour=h, minute=m)
    for h, m in [(7, 30), (9, 15), (11, 00), (12, 45), (14, 30), (16, 15), (18, 00)]
]


def visualize_timetable(timetable):
    fig, ax = plt.subplots(figsize=(12, 6))

    # Group events by day and sort by start time
    grouped_events = {day: [] for day in days_order}
    for event in timetable:
        grouped_events[event["day"]].append(event)

    for day in grouped_events:
        grouped_events[day].sort(key=lambda e: e["starttime"])

    # pprint(grouped_events)

    # Compute rows for overlapping events
    plotted_events = []
    day_rows = dict()
    prefix_rows = {-1: 0}
    for day, events in grouped_events.items():
        used_rows = []  # Track active rows for events
        for event in events:
            start = (
                datetime.strptime(event["starttime"], "%H:%M").hour
                + datetime.strptime(event["starttime"], "%H:%M").minute / 60
            )
            end = (
                datetime.strptime(event["endtime"], "%H:%M").hour
                + datetime.strptime(event["endtime"], "%H:%M").minute / 60
            )

            # Find an available row for the event
            row = 0
            while row < len(used_rows) and used_rows[row] > start:
                row += 1
            if row == len(used_rows):
                used_rows.append(end)  # Add a new row
            else:
                used_rows[row] = end  # Update the row's end time

            plotted_events.append((prefix_rows[day - 1] + row + 0.5, start, end, event))
        day_rows[day] = len(used_rows)
        prefix_rows[day] = prefix_rows[day - 1] + max(1, day_rows[day])

    # Plot the events
    for y_position, start, end, event in plotted_events:
        ax.barh(
            -y_position,
            end - start,
            left=start,
            color=name_to_color(event["name"]),
            edgecolor="black",
        )
        ax.text(
            start + (end - start) / 2,
            -y_position,
            f"{event['name']} - {event["type"]}\n{event["teachers"]}\n{event['room']}",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
        )

    prefix_rows[len(days_order)] = prefix_rows[len(days_order) - 1] + 1

    # Set y-axis labels and ticks
    ticks = list(map(lambda x: -(prefix_rows[x - 1] + prefix_rows[x]) / 2, days_order))

    for day in days_order:
        ax.axhspan(
            -prefix_rows[day - 1],
            -prefix_rows[day],
            color="lightgray" if day % 2 == 0 else "white",
            alpha=0.5,
        )
    #
    # for day in days_order:
    #     print(
    #         dict(
    #             s=prefix_rows[day - 1],
    #             e=prefix_rows[day],
    #             color="lightgray" if day % 2 == 0 else "white",
    #             alpha=0.2,
    #         )
    #     )

    ax.set_yticks(ticks)
    # print(ticks)
    # print(prefix_rows)
    ax.set_yticklabels(days_names)
    ax.set_xticks(list(map(lambda x: x.hour + x.minute / 60, hour_start_times)))
    ax.set_xticklabels(list(map(lambda x: x.strftime("%H:%M"), hour_start_times)))
    ax.set_xlabel("Time (hours)")
    ax.set_title("Weekly Timetable")

    # Adjust limits and add grid
    # ax.set_ylim(len(days_order) - 0.5, -0.5)
    ax.grid(axis="x", linestyle="--", alpha=0.7)

    return fig


def visualize_timetable_html(timetable):
    grouped_events = {day: [] for day in days_order}
    for event in timetable:
        grouped_events[event["day"]].append(event)

    for day in grouped_events:
        grouped_events[day].sort(key=lambda e: e["starttime"])

    # pprint(grouped_events)

    # Compute rows for overlapping events
    plotted_events = []
    min_time = 24
    max_time = 0
    for day, events in grouped_events.items():
        used_rows = []  # Track active rows for events
        plotted_events.append([])
        for event in events:
            start = (
                datetime.strptime(event["starttime"], "%H:%M").hour
                + datetime.strptime(event["starttime"], "%H:%M").minute / 60
            )
            min_time = min(min_time, start)
            end = (
                datetime.strptime(event["endtime"], "%H:%M").hour
                + datetime.strptime(event["endtime"], "%H:%M").minute / 60
            )
            max_time = max(max_time, end)

            # Find an available row for the event
            row = 0
            while row < len(used_rows) and used_rows[row] > start:
                row += 1
            if row == len(used_rows):
                used_rows.append(end)  # Add a new row
            else:
                used_rows[row] = end  # Update the row's end time

            while len(plotted_events[-1]) < row + 1:
                plotted_events[-1].append([])
            plotted_events[-1][row].append((start, end, event))

    out = '<div class="ctm-table">'
    lenght = max_time - min_time
    for i, day in enumerate(plotted_events):
        out += f'<div class="ctm-day" style="height:{max(4, 4 * len(day))}rem">'
        out += f'<div class="ctm-day-label">{days_names[i]}</div>'
        out += '<div class="ctm-day-rows">'
        for row in day:
            out += '<div class="ctm-row">'
            for event in row:
                out += f'<div class="ctm-event" style="width:{(event[1] - event[0]) * 100 / lenght}%;left:{(event[0] - min_time) * 100 / lenght}%">'
                out += (
                    event[2]["type"]
                    + " - "
                    + event[2]["name"]
                    + "<br>"
                    + event[2]["teachers"]
                    + "<br>"
                    + event[2]["room"]
                )
                out += "</div>"
            out += "</div>"
        out += "</div>"
        out += "</div>"

    out += "</div>"
    return out


# visualize_timetable(timetable)
