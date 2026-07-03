#pragma once

#include <map>
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

inline nlohmann::json StringMapToJson(const std::map<std::string, std::string>& values)
{
    nlohmann::json out = nlohmann::json::object();
    for (const auto& [key, value] : values) {
        out[key] = value;
    }
    return out;
}

inline nlohmann::json StringVectorToJson(const std::vector<std::string>& values)
{
    nlohmann::json out = nlohmann::json::array();
    for (const auto& value : values) {
        out.push_back(value);
    }
    return out;
}

struct AvatarPropertyDebugState {
    unsigned int avatar_index = 0;
    bool success = false;
    std::string unit = "raw";
    std::string last_message;
    std::map<std::string, std::string> requested_properties;
    std::map<std::string, std::string> properties_before;
    std::map<std::string, std::string> properties_after;
    std::vector<std::string> changed_keys;
    std::vector<std::string> missing_after_keys;
};

inline nlohmann::json BuildAvatarPropertyDebugJson(const AvatarPropertyDebugState& state)
{
    return {
        {"success", true},
        {"avatar_index", state.avatar_index},
        {"apply_success", state.success},
        {"unit", state.unit},
        {"requested_properties", StringMapToJson(state.requested_properties)},
        {"properties_before", StringMapToJson(state.properties_before)},
        {"properties_after", StringMapToJson(state.properties_after)},
        {"changed_keys", StringVectorToJson(state.changed_keys)},
        {"missing_after_keys", StringVectorToJson(state.missing_after_keys)},
        {"last_message", state.last_message}
    };
}
