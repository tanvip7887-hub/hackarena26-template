def analyze_behavior(features):

    insights = []

    if features["zone_approach"] > 0.6 and features["loitering"] > 10:
        insights.append({
            "priority": 1,
            "factor": "Zone Surveillance",
            "reason": "Individual stayed near restricted zone for extended time."
        })

    if features["speed"] > 180:
        insights.append({
            "priority": 2,
            "factor": "Rapid Movement",
            "reason": "Movement speed higher than normal walking."
        })

    if features["freeze_time"] > 12:
        insights.append({
            "priority": 3,
            "factor": "Stationary Monitoring",
            "reason": "Person remained stationary while observing area."
        })

    if features["crowd"] > 1:
        insights.append({
            "priority": 4,
            "factor": "Group Presence",
            "reason": "Multiple individuals detected near monitored location."
        })

    return sorted(insights, key=lambda x: x["priority"])


def build_explanation(risk, insights):

    text = f"Risk Level: {risk}\n"
    text += "Key Behaviour Factors:\n"

    if not insights:
        text += "- No major behaviour factors detected\n"
    else:
        for i in insights:
            text += f"- {i['factor']}: {i['reason']}\n"

    return text