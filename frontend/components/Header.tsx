"use client";

import { useEffect, useState } from "react";
import BrandLogo from "@/components/BrandLogo";
import CurrencySelect from "@/components/CurrencySelect";
import LanguageSelect from "@/components/LanguageSelect";
import NavItems from "@/components/NavItems";
import SearchDialog from "@/components/SearchDialog";
import UserMenu from "@/components/UserMenu";

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <header className="header sticky top-0">
        <div className="container header-wrapper">
          <BrandLogo />
          <nav className="hidden sm:block">
            <NavItems onSearch={() => setSearchOpen(true)} />
          </nav>
          <div className="flex items-center gap-2">
            <CurrencySelect />
            <LanguageSelect />
            <UserMenu onSearch={() => setSearchOpen(true)} />
          </div>
        </div>
      </header>
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
