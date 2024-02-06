#!/usr/bin/php
<?php
function testBrotli()
{
    $stringToCompress = "Ahoj světe";
    $decoded = brotli_uncompress(brotli_compress($stringToCompress));
    assert($stringToCompress === $decoded);
}

function testZstd()
{
    $stringToCompress = "Ahoj světe";
    $decoded = zstd_uncompress(zstd_compress($stringToCompress));
    assert($stringToCompress === $decoded);
}

function testIgbinary()
{
    $dataToSerialize = ["Ahoj" => "světe"];
    $deserialized = igbinary_unserialize(igbinary_serialize($dataToSerialize));
    assert($dataToSerialize === $deserialized);
}

function testSsdeep()
{
    $hash = ssdeep_fuzzy_hash("ahoj světe");
    assert(is_string($hash));

    $result = ssdeep_fuzzy_compare('24:FPlUMKVsgNfgmjFadP6WboWjb8tsH4RSXqMbLFpjwPDt4tFF:9lUajiiPbbnr4RSXqMbppMZ4t3', '48:9lUajiiPbbnr4RSXqMbLbmo03Rcq0K/cvhQ+3/M8M5BEaB6:9HFHsGqabmoMR18hQ+308sBdk');
    assert($result === 57);
}

testBrotli();
testZstd();
testIgbinary();
testSsdeep();