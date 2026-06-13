"""Unit tests for ImportService parsing and validation."""

import tempfile
from pathlib import Path

import pytest

from app.services.import_service import ImportService


@pytest.fixture
def svc():
    return ImportService()


@pytest.fixture
def sample_csv_path():
    """Create a temporary CSV file matching the COMSTAR format."""
    lines = [
        ",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,原始交易查询与维护,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,",
        "选择导入,选择投组,分配状态,期权类型,策略编号,策略成交编号,Leg,投组,交易事件类型,交易目的,货币对,成交编号,操作人,交易性质,本方,本方交易员,对手方,交易日,交易时间,自然日,交易方向,交易类型,期权费支付日,期限,行权日,时区,行权截止时间,交割日,执行价,交易货币,货币1金额,货币2金额,回报金额,回报货币,障碍类型,障碍方向,障碍线,观测起始日,观测结束日,期权费类型,期权费率,期权费金额,期权费货币,即期汇率,波动率,波动率标的,成本期权费率,成本期权费金额,客户利润,交割类型,交割货币,交割参考汇率,交割轧差汇率,行权状态,生效状态,行权交易员,行权时间,行权方法,行权衍生交易的成交编号,行权衍生交易的交易编号,Delta Exchange交易成交编号,Delta Exchange交易编号,Delta Exchange交易产品类型,亚式期权子类型,平均计算方法,平均价格计算起始日,平均价格计算结束日,参考假日,频率,平均价格舍入方式,平均价格小数位数,交割状态,备注,事件备注,来源,原始交易系统编号,交易场所,清算机构,经纪人,清算方式,复核编号,创建时间,是否关联方交易,是否到期自动行权,是否有原始交易,行权衍生的交易品种,操作事件",
        "false, ,完成分配或匹配,Plain Vanilla, , , ,期权-对外平盘-金市,正常,银行间交易,USD/CNY,6.2.9999001,测试用户A, , ,dealer.test@samplebank,示例银行A(SAMPLEA),2026-06-08,15:26:43,2026-06-08,卖出,CALL,2026-06-10,BROKEN,2026-06-12,Beijing,15:00:00,2026-06-16,7.1200,USD,10000000.00,71200000.00, , , , , , , ,Pips,15,15000.00,CNY,7.1150,1.2500, , , , ,全额交割, , , ,未行权, , , , , , , , , , , , , , , , , ,未交割, , ,CSTP下载交易,2202606084000999999,CFETS,其它, ,双边全额清算,O99990001,2026-06-08 15:26:47, , ,不适用, ,",
    ]

    # Write in text mode with utf-8 encoding
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("\n".join(lines))
        filepath = f.name

    yield filepath

    # Cleanup
    try:
        Path(filepath).unlink()
    except OSError:
        pass


class TestParseFile:
    def test_parses_valid_csv(self, svc, sample_csv_path):
        """Should parse a COMSTAR CSV and return ParsedImportData."""
        parsed = svc.parse_file(sample_csv_path)
        assert parsed.filename.endswith(".csv")
        assert parsed.total_rows == 1
        assert len(parsed.column_mapping) > 0

    def test_parsed_row_has_expected_fields(self, svc, sample_csv_path):
        """Parsed rows should contain the mapped fields."""
        parsed = svc.parse_file(sample_csv_path)
        validated = svc.validate(parsed)
        assert validated.valid_count > 0
        row = validated.valid_rows[0]
        assert row["trade_id"] == "6.2.9999001"
        assert row["ccy_pair"] == "USD/CNY"
        assert row["trade_type"] == "CALL"


class TestValidate:
    def test_detects_required_fields(self, svc):
        """Validation should flag rows missing required fields."""
        from app.utils.excel_parser import ParsedImportData

        parsed = ParsedImportData(
            filename="test.csv",
            file_hash="abc",
            rows=[{"成交编号": ""}],
            column_mapping={"成交编号": "trade_id"},
        )
        validated = svc.validate(parsed)
        assert validated.error_count > 0
