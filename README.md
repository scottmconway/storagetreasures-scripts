# Storage Treasures Scripts
A collection of scripts for programmatically interacting with [StorageTreasures](https://www.storagetreasures.com).

At this time, the project is "read-only", and only used to update on new query results.
Time alerts on watched auctions and auction auto-bidding may be added in the future.

## Requirements
* python3
* see requirements.txt

## Configuration Setup
See `config.json.example` for an example configuration file.

### `logging`
`log_level` - sets the log level to subscribe to
`gotify` - only required if you wish to use gotify as a logging destination (see the example config for what you can do here)

### `seen_listings_filename`
This is the path of the file that will have "seen" listings written to, so we can track "new" ones. This is used by `alert_on_new_query_results.py`, and should probably be moved elsewhere.

### `saved_queries`
This section contains `{query_friendly_name: query}` JSON objects, for use by `alert_on_new_query_results.py`. `query` should be a query JSON, as described below.

## Scripts
### `alert_on_new_query_results.py`

This script executes a query as specified by the user, and logs results that haven't been seen before. "Seen listings" are tracked globally across all queries, so you should only be alerted once about a given item.

Queries require the `search_term`, `search_term`, and `search_radius_miles` parameters, and may optionally include `filter_types`, `filter_categories`, and `unit_contents`.
See `config.json.example`'s `saved_queries` section for examples.

#### Arguments
|Short Name|Long Name|Type|Description|
|-|-|-|-|
|`-q`|`--query-name`|`str`|The name of the query to execute. This must be present in the data source's list of queries|
|N/A|`--all`|`bool`|If set, execute all queries under the configured data source|
|N/A|`--log-images`|`bool`|If set, log image hyperlinks in markdown format (useful for gotify)|
|`-l`|`--list-queries`|`bool`|If set, list all queries that can be executed by this data source and exit|
