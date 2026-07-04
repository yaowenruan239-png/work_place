#include "vector_index.h"

#include <exception>
#include <iostream>
#include <string>
#include <vector>

#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace {

constexpr const char* kHost = "0.0.0.0";
constexpr int kPort = 8080;

void write_json(httplib::Response& res, int status, const json& body) {
    res.status = status;
    res.set_content(body.dump(), "application/json");
}

void write_error(httplib::Response& res, int status, const std::string& message) {
    write_json(res, status, json{{"ok", false}, {"error", message}});
}

json parse_json_body(const httplib::Request& req) {
    try {
        return json::parse(req.body);
    } catch (const json::parse_error& exc) {
        throw std::invalid_argument(std::string("invalid JSON: ") + exc.what());
    }
}

std::vector<float> parse_vector_field(const json& body, const std::string& field_name) {
    if (!body.contains(field_name)) {
        throw std::invalid_argument("missing field: " + field_name);
    }
    if (!body.at(field_name).is_array()) {
        throw std::invalid_argument(field_name + " must be an array");
    }

    std::vector<float> vector;
    vector.reserve(body.at(field_name).size());
    for (const auto& item : body.at(field_name)) {
        if (!item.is_number()) {
            throw std::invalid_argument(field_name + " must contain only numbers");
        }
        vector.push_back(item.get<float>());
    }
    return vector;
}

long long parse_memory_id(const json& body) {
    if (!body.contains("memory_id")) {
        throw std::invalid_argument("missing field: memory_id");
    }
    if (!body.at("memory_id").is_number_integer()) {
        throw std::invalid_argument("memory_id must be an integer");
    }
    return body.at("memory_id").get<long long>();
}

int parse_top_k(const json& body) {
    if (!body.contains("top_k")) {
        throw std::invalid_argument("missing field: top_k");
    }
    if (!body.at("top_k").is_number_integer()) {
        throw std::invalid_argument("top_k must be an integer");
    }
    return body.at("top_k").get<int>();
}

}  // namespace

int main() {
    VectorIndex index;
    httplib::Server server;

    server.Get("/health", [&index](const httplib::Request&, httplib::Response& res) {
        write_json(res, 200, json{{"status", "ok"}, {"index_size", index.size()}});
    });

    server.Post("/index/clear", [&index](const httplib::Request&, httplib::Response& res) {
        index.clear();
        write_json(res, 200, json{{"ok", true}, {"index_size", 0}});
    });

    server.Post("/index/add", [&index](const httplib::Request& req, httplib::Response& res) {
        try {
            const auto body = parse_json_body(req);
            const auto memory_id = parse_memory_id(body);
            const auto vector = parse_vector_field(body, "vector");

            index.add(memory_id, vector);
            write_json(
                res,
                200,
                json{{"ok", true}, {"memory_id", memory_id}, {"index_size", index.size()}}
            );
        } catch (const std::invalid_argument& exc) {
            write_error(res, 400, exc.what());
        } catch (const std::exception& exc) {
            write_error(res, 500, exc.what());
        }
    });

    server.Post("/index/search", [&index](const httplib::Request& req, httplib::Response& res) {
        try {
            const auto body = parse_json_body(req);
            const auto vector = parse_vector_field(body, "vector");
            const auto top_k = parse_top_k(body);
            const auto results = index.search(vector, top_k);

            json result_items = json::array();
            for (const auto& result : results) {
                result_items.push_back(json{{"memory_id", result.memory_id}, {"score", result.score}});
            }

            write_json(res, 200, json{{"ok", true}, {"results", result_items}});
        } catch (const std::invalid_argument& exc) {
            write_error(res, 400, exc.what());
        } catch (const std::exception& exc) {
            write_error(res, 500, exc.what());
        }
    });

    std::cout << "agent_memory_service listening on " << kHost << ":" << kPort << std::endl;
    if (!server.listen(kHost, kPort)) {
        std::cerr << "failed to listen on " << kHost << ":" << kPort << std::endl;
        return 1;
    }
    return 0;
}
