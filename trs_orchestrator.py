print("DEBUG: Today received:", today)
print("DEBUG: Current dates length:", len(data.get("dates", [])))
# Force append today's date if not present
current_date_str = today.strftime('%Y-%m-%d') if today else date.today().strftime('%Y-%m-%d')
if "dates" in data and current_date_str not in data["dates"][-1:]:
    data["dates"].append(current_date_str)
    print("DEBUG: Appended date:", current_date_str)
# Then in models loop (for each model):
# Find where scores appended
# Add: model["scores"].append(computed_trs_for_model)  # force if logic skips
