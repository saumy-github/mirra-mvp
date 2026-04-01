#pragma once

#include <string>
#include <vector>
#include <json.hpp>

struct NativeAvatarDebugState {
    std::string last_native_avatar_path;
    bool last_native_avatar_success = false;
    std::string last_measurement_csv_path;
    bool last_measurement_csv_success = false;
    std::string last_measurement_template_path;
    std::string last_message;
};

inline nlohmann::json BuildNativeAvatarDebugJson(
    const NativeAvatarDebugState& state,
    int arrangementSlotCount = 0,
    int patternArrangementCount = 0,
    int patternCount = 0,
    const std::vector<std::string>& slotNames = {}
)
{
    nlohmann::json slotNameArray = nlohmann::json::array();
    for (const auto& name : slotNames) {
        slotNameArray.push_back(name);
    }

    return {
        {"success", true},
        {"native_avatar_import", {
            {"path", state.last_native_avatar_path},
            {"success", state.last_native_avatar_success}
        }},
        {"measurement_import", {
            {"csv_path", state.last_measurement_csv_path},
            {"template_path", state.last_measurement_template_path},
            {"success", state.last_measurement_csv_success}
        }},
        {"pattern_count", patternCount},
        {"arrangement_list_populated", arrangementSlotCount > 0},
        {"arrangement_slot_count", arrangementSlotCount},
        {"pattern_arrangement_count", patternArrangementCount},
        {"slot_names", slotNameArray},
        {"last_message", state.last_message}
    };
}
