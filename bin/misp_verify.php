#!/usr/bin/php
<?php
function testBrotli()
{
    $stringToCompress = "Ahoj světe";
    $decoded = brotli_uncompress(brotli_compress($stringToCompress));
    assert($stringToCompress == $decoded);
}

function testZstd()
{
    $stringToCompress = "Ahoj světe";
    $decoded = zstd_uncompress(zstd_compress($stringToCompress));
    assert($stringToCompress == $decoded);
}

function testIgbinary()
{
    $dataToSerialize = ["Ahoj" => "světe"];
    $deserialized = igbinary_unserialize(igbinary_serialize($dataToSerialize));
    assert($dataToSerialize == $deserialized);
}

function testSsdeep()
{
    $hash = ssdeep_fuzzy_hash("ahoj světe");
    assert(is_string($hash));
}

testBrotli();
testZstd();
testIgbinary();
testSsdeep();