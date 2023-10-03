# Awesome Axonius Queries

## Background and Motivation

During our work, many non obvious queries were created in Axonius, and many of them share quite a few principles.
The purpose of this document is to share the most useful queries, and explain a bit about the principles behind them, and how to use them correctly.

## Principles of Queries and Dashboards
### Building blocks

When planning a dashboard chart in Axonius to track a policy, we first need to identify the set of entities to which the policy applies. For example, for the policy, “every server must have splunk client installed”, the relevant set of entities is “servers”.
Next, we aim to define for each policy:
* Coverage - entities that comply with the policy.
* Gap - entities that are non-compliant with the policy.
* Unknown (optional) - when we don’t have information to decide if an entity is compliant or non-compliant.
* Exceptions (optional) - when we know the entity is non compliant but it is “ok” because of an approved exception. Exceptions may be permanent or temporary.
* In-progress (optional) - when we know the entity is non compliant, but work on making it compliant is in-progress. Technically this is similar to a temporary exception.

Each such defined set of policies - they should complement each other, such that the set of defined queries should sum up to the **base set of entities**:

> **coverage + gap + unknown + exceptions + in-progress = base set of entities**

### Priorities

Next, weed to define our priority for the tracking of the policy - are we aiming to minimize false-positives, which means, if we get a result we will be more confident it is correct, or minimize false-negatives, which means that if an entity has a problem we will be more confident it will come up in the gap. These two priorities are naturally in conflict with each other.

Normally we will choose to minimize false-positives, but this may change with different organizations, policies, and graphs.
### Steps
#### Base set of entities
In order to implement the above, we first need to define an Axonius query for the basic set of entities. In our splunk example - that would be servers. Note, that just finding all possible servers is not good enough. The reason is that some records might not be up-to-date, so we want to limit our scope to servers for which we have up-to-date data.

The usual approach to do so is to filter on “last-seen” within the last 30/45/60 days, however, this might not be good enough, because some Axonius integrations don’t remove deleted entities, and so for example, the fact that the device was “last seen” yesterday, might just mean that Active-Directory retained the record even though the server itself is long gone.

When defining the query, we might also want to take into account other issues of relevance, for example, some policies might only apply to windows servers and not all servers, or not apply to VMs on ESXi. (although that might be considered an exception, pay attention!)

#### Finding the gap
The next step is to research the gap. Starting from the base set of entities, try to narrow down the query until you get to a subset of entities for which you are certain they are non compliant.

Remember that for control coverage, e.g. “no Crowdstrike”, an endpoint might not have Crowdstrike either if there is no Crowdstrike adapter connection, or if there is a connection but the last seen is very old (e.g. 45 days).

#### Defining the coverage
Once we have the gap defined, we should define the coverage query. We should be careful here though, as sometimes, in order to avoid false positives, the gap includes additional limitations whose negation does not imply that the entity is covered.

For example, when looking at “Servers without Splunk client”, we can’t say for sure that a server does not have a Splunk forwarder if we have no information at all about installed software. So, in this case, this should not be part of the coverage query, but part of the “unknown” query. Note, just because it’s only “unknown” doesn’t mean it’s not a problem - it might be a different problem! In this case - lack of visibility - perhaps some other control (e.g. SCCM) does not cover the server.

#### Defining Exceptions

The best way to manage exceptions in Axonius is using tags. Permanent exceptions should be represented by a regular tag, which we recommend to color appropriately.
Temporary exceptions should be represented by a tag with an expiration date, usually defined by a certain number of days from the time the tag was set.
* For exceptions - define a query that only selects on the tags for permanent and temporary exceptions.
* For in-progress - define a query that only selects on the tags that represent that work on the entity is in-progress. We recommended to always give an expiration date to the in-progress tag, so that entities don’t get “stuck” in the “in-progress” status, become forgotten and then ignored.

#### Defining Dashboards Charts
The straightforward approach for defining a chart in an Axonius dashboard is the following:
* Set a query comparison chart, pick bar chart or a pie chart
* For simple queries (no exceptions or in-progress) add the coverage query in green and label it “Compliant”. Add the gap query in red and label it “Non-compliant”.
* If defined, add the unknown query in yellow.
* If defined, add exceptions and in progress in a color that matches your organization's approach and the specific query, it may be another shade of red, another shade of green, or also yellow.

For charts with exceptions, we have a problem, as the exceptions and in-progress queries are subsets of the gap query. In this case, we will need to define three new queries:

* Add a new query “non-compliant” - it should be:
`Gap & (!exception) & (!in-progress)`
* Add a new query “exception” - it should be:
`Gap & exception`
* Add a new query “in-progress” - it should be:
`Gap & in-progress`

(Note: we assume that there isn't an overlap between the exception and in-progress queries.)

## Useful Queries

### MFA Gap

* consider splitting to admins, domain admins, etc.

```
("specific_data.data.account_disabled" == false) and ("specific_data.data.is_locked" == false) and not (("specific_data.data.user_factors" == match([("factor_type" == "Password") and (not ("factor_status" == regex("notAllowedByPolicy", "i")))])) and ("specific_data.data.user_factors" == match([(not ("factor_type" == "Password")) and (not ("factor_status" == regex("notAllowedByPolicy", "i")))]))) and ("adapters_data.azure_ad_adapter.user_type" == "Member") and (("adapters_data.azure_ad_adapter.username" == ({"$exists":true,"$ne":""}))) and ((("specific_data.data.user_factors" == ({"$exists":true,"$ne":[]})) and "specific_data.data.user_factors" != [])) and not ("specific_data.data.user_created" >= date("NOW - 14d"))
```

### Encryption Gap

* consider splitting to laptops and non-laptops

```
"specific_data" == match([plugin_name not in ['service_now_adapter'] and (("data.hard_drives.is_encrypted" == false) and (("data.hard_drives.free_size" == ({"$exists":true,"$ne":null}))))])
```

### Devices with close (30 days) or past CISA due date:

```
("specific_data" == match([("data.cisa_vulnerabilities.due_date" >= date("NOW + 0h") and "data.cisa_vulnerabilities.due_date" <= date("NOW + 30d"))]) or ("specific_data.data.cisa_vulnerabilities.due_date" >= date("NOW - 10000d"))) and ("specific_data.data.last_seen" >= date("NOW - 30d"))
```

### Simple Agent or adapter coverage

* For example, this is for intune, but it will work for other adapters, e.g. crowdstrike, sentinelone etc.
* Sometimes it is necessary limit the reference list of devices, as some agents are only relevant for some devices

```
("specific_data.data.last_seen" >= date("NOW - 30d")) and not ((("adapters_data.azure_ad_adapter.id" == ({"$exists":true,"$ne":""}))) and ("adapters_data.azure_ad_adapter.last_seen" >= date("NOW - 30d")))
```

### Cyberark EPM Coverage

* This is not a simple adapter coverage query as it requires checking both the agent and installed software

```
("specific_data.data.last_seen" >= date("NOW - 30d")) and ((("specific_data.data.installed_software" == ({"$exists":true,"$ne":[]})) and "specific_data.data.installed_software" != [])) and not (((("adapters_data.cyberark_epm_adapter.id" == ({"$exists":true,"$ne":""}))) and ("adapters_data.cyberark_epm_adapter.last_seen" >= date("NOW - 30d"))) or ("specific_data.data.installed_software.name" == regex("cyberark endpoint", "i")))
```

### Splunk coverage

* It's recommended to combine this query with a "servers last seen 30 days" that's correct for your organization
* The value of the splunk coverage query is to make sure that all server logs are collected

```
not ("specific_data.data.installed_software" == match([((("name" == regex("forwarder", "i")) and (("publisher" == regex("splunk", "i")) or ("vendor" == regex("splunk", "i")))) or ("name" == regex("splunk", "i")))])) and (((("adapters_data.tenable_io_adapter.agent_uuid" == ({"$exists":true,"$ne":""}))) and ("adapters_data.tenable_io_adapter.has_agent" == true)) or (("adapters_data.sccm_adapter.id" == ({"$exists":true,"$ne":""})))) and ((("specific_data.data.installed_software" == ({"$exists":true,"$ne":[]})) and "specific_data.data.installed_software" != []))
```

### CSPM example

* combine as necessary a CSPM provider (e.g. Wiz, Orca, etc.) with one or more cloud providers (e.g. AWS)
* Consider also checking the other way around - that the cloud provider adapter also has full coverage, i.e. that all devices covered by Wiz are also covered by the AWS adapter.

```
(("adapters_data.aws_adapter.id" == ({"$exists":true,"$ne":""}))) and ("adapters_data.aws_adapter.last_seen" >= date("NOW - 30d")) and (not (("adapters_data.wiz_adapter.id" == ({"$exists":true,"$ne":""}))) or not ("adapters_data.wiz_adapter.last_seen" >= date("NOW - 30d"))) and ("specific_data.data.power_state" in ["Migrating","Normal","Rebooting","StartingUp"])
```

### Never logged in old users

* consider splitting to service accounts and non service accounts

```
not ("specific_data.data.user_created" >= date("NOW - 365d")) and ("specific_data.data.logon_count" == 0) and ("specific_data.data.account_disabled" == false) and ("specific_data.data.account_expired" == false) and ("specific_data.data.is_locked" == false) and ("adapters_data.active_directory_adapter.account_lockout" == false) and not ("specific_data.data.last_logon" >= date("NOW - 1000d")) and not ("specific_data.data.last_logon_timestamp" >= date("NOW - 1000d"))
```

