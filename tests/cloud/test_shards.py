from pneuma_lab.cloud.shards import shard_range


def test_contiguous_shards_cover_one_topology_once() -> None:
    assert list(shard_range(0, 3, 10)) + list(shard_range(1, 3, 10)) + list(shard_range(2, 3, 10)) == list(range(10))
